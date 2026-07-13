import os
from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List
from io import BytesIO

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.database import get_db
from app.db.placement_models import (
    PlacementOffer,
    PlacementOfferCapPolicy,
    PlacementApplication,
    PlacementDrive,
    PlacementCompany,
    PlacementPostPlacement,
)
from app.db.models import PLMStudentProfile, IEMStudents, IEMSAcademicBatch
from app.utils.auth_helper import get_current_user
from app.utils.http_return_helper import returnException, returnSuccess

from app.api.v1.placement_module.offer_schema import (
    OfferCreateSchema,
    OfferUpdateSchema,
)

# ReportLab imports for professional PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

router = APIRouter()

def handle_offer_status_change(db: Session, profile_id: int, old_status: str, new_status: str, org_id: int, offer_id: Optional[int] = None, recorded_by: Optional[int] = None):
    """
    Manages active offer count and locks/unlocks the student profile 
    depending on offer status transition (e.g. accepted, declined, revoked).
    """
    profile = db.query(PLMStudentProfile).filter(PLMStudentProfile.profile_id == profile_id).first()
    if not profile:
        return

    if profile.active_offer_count is None:
        profile.active_offer_count = 0

    # 1. Update active offer count based on transitions
    if old_status != "ACCEPTED" and new_status == "ACCEPTED":
        profile.active_offer_count += 1
    elif old_status == "ACCEPTED" and new_status != "ACCEPTED":
        profile.active_offer_count = max(0, profile.active_offer_count - 1)

    # 2. Update placement_status
    if profile.active_offer_count > 0:
        profile.placement_status = "PLACED"
    else:
        profile.placement_status = "UNPLACED"

    # 3. Check Offer Cap Policy
    student = db.query(IEMStudents).filter(IEMStudents.student_id == profile.student_id).first()
    batch_year = None
    if student and student.academic_batch_id:
        batch = db.query(IEMSAcademicBatch).filter(IEMSAcademicBatch.academic_batch_id == student.academic_batch_id).first()
        if batch:
            batch_year = batch.start_year

    if batch_year:
        policy = db.query(PlacementOfferCapPolicy).filter(
            PlacementOfferCapPolicy.tenant_id == org_id,
            PlacementOfferCapPolicy.batch_year == batch_year
        ).first()

        if policy:
            if not policy.allow_multiple:
                profile.is_locked = 1 if profile.active_offer_count >= 1 else 0
            elif profile.active_offer_count >= policy.max_offers_per_student:
                profile.is_locked = 1
            else:
                profile.is_locked = 0
        else:
            # Default fallback policy: Lock on 1st offer
            if profile.active_offer_count >= 1:
                profile.is_locked = 1
            else:
                profile.is_locked = 0
    else:
        # Fallback if no batch found: Lock on 1st offer
        if profile.active_offer_count >= 1:
            profile.is_locked = 1
        else:
            profile.is_locked = 0

    # Auto-create Post-Placement record when status transitions to ACCEPTED
    if offer_id and new_status == "ACCEPTED":
        pp = db.query(PlacementPostPlacement).filter(PlacementPostPlacement.offer_id == offer_id).first()
        if not pp:
            offer = db.query(PlacementOffer).filter(PlacementOffer.offer_id == offer_id).first()
            proposed_joining = offer.joining_date if offer else None
            
            new_pp = PlacementPostPlacement(
                offer_id=offer_id,
                joining_confirmation_date=datetime.now().date(),
                actual_joining_date=proposed_joining,
                status="CONFIRMED",
                recorded_by=recorded_by or 1,
                recorded_at=datetime.now()
            )
            db.add(new_pp)


# --- Status Mapping Helpers ---
def map_db_status_to_frontend(db_status: str, generated_from_template: bool = False) -> str:
    if db_status == "ISSUED":
        return "Generated" if generated_from_template else "Sent"
    elif db_status == "ACCEPTED":
        return "Accepted"
    elif db_status == "DECLINED":
        return "Rejected"
    elif db_status == "REVOKED":
        return "Revoked"
    return "Sent"

def map_frontend_status_to_db(fe_status: str) -> str:
    if fe_status in ["Generated", "Sent", "ISSUED"]:
        return "ISSUED"
    elif fe_status in ["Accepted", "ACCEPTED"]:
        return "ACCEPTED"
    elif fe_status in ["Rejected", "DECLINED"]:
        return "DECLINED"
    elif fe_status in ["Revoked", "REVOKED"]:
        return "REVOKED"
    return "ISSUED"


# --- REST API Endpoints ---

@router.get("/list")
def list_offers(
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        results = (
            db.query(
                PlacementOffer.offer_id,
                PlacementOffer.tenant_id,
                PlacementOffer.application_id,
                PlacementOffer.drive_id,
                PlacementOffer.profile_id,
                PlacementOffer.ctc,
                PlacementOffer.role,
                PlacementOffer.location,
                PlacementOffer.joining_date,
                PlacementOffer.offer_letter_path,
                PlacementOffer.is_ppo,
                PlacementOffer.status,
                PlacementOffer.issued_at,
                PlacementOffer.accepted_at,
                PlacementOffer.declined_at,
                PlacementOffer.revoked_at,
                PlacementOffer.decline_reason,
                PlacementOffer.revoke_reason,
                PlacementOffer.generated_from_template,
                PlacementOffer.template_id,
                PlacementDrive.drive_name,
                PlacementCompany.company_id,
                PlacementCompany.company_name,
                IEMStudents.name.label("student_name"),
                IEMStudents.usno.label("usn"),
                IEMStudents.student_id
            )
            .join(PlacementDrive, PlacementDrive.drive_id == PlacementOffer.drive_id)
            .join(PlacementCompany, PlacementCompany.company_id == PlacementDrive.company_id)
            .join(PLMStudentProfile, PLMStudentProfile.profile_id == PlacementOffer.profile_id)
            .join(IEMStudents, IEMStudents.student_id == PLMStudentProfile.student_id)
            .filter(PlacementOffer.tenant_id == org_id)
            .all()
        )

        offers_list = []
        for r in results:
            # Determine appropriate remarks
            remarks = ""
            if r.status == "DECLINED" and r.decline_reason:
                remarks = r.decline_reason
            elif r.status == "REVOKED" and r.revoke_reason:
                remarks = r.revoke_reason

            offers_list.append({
                "id": r.offer_id,
                "company_id": r.company_id,
                "company_name": r.company_name,
                "drive_id": r.drive_id,
                "drive_name": r.drive_name,
                "student_id": r.student_id,  # student_id of IEMStudents
                "student_name": r.student_name,
                "usn": r.usn,
                "designation": r.role,
                "package_ctc": str(r.ctc) if r.ctc else "0.0",
                "location": r.role, # Job location or fallback designation
                "location_real": r.location, # Keep real location
                "offer_date": str(r.issued_at.date()) if r.issued_at else None,
                "joining_date": str(r.joining_date) if r.joining_date else None,
                "status": map_db_status_to_frontend(r.status, bool(r.generated_from_template)),
                "remarks": remarks,
                "created_by_name": "TPO Office"
            })

        # Correct location field to return real location rather than role
        for o in offers_list:
            o["location"] = o["location_real"] or "N/A"
            del o["location_real"]

        return returnSuccess(offers_list)
    except Exception as e:
        return returnException(str(e))


@router.post("/save")
def create_offer(
    data: OfferCreateSchema,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        # 1. Resolve student profile from student_id
        profile = db.query(PLMStudentProfile).filter(PLMStudentProfile.student_id == data.student_id).first()
        if not profile:
            return returnException(f"Placement profile not found for student ID {data.student_id}.")

        # 2. Check if student is locked before issuing an offer
        if profile.is_locked:
            return returnException("This student's placement profile is locked (policy limit reached). Cannot issue new offer.")

        # 3. Resolve or create application
        app = db.query(PlacementApplication).filter(
            PlacementApplication.profile_id == profile.profile_id,
            PlacementApplication.drive_id == data.drive_id
        ).first()

        if not app:
            app = PlacementApplication(
                tenant_id=org_id,
                drive_id=data.drive_id,
                profile_id=profile.profile_id,
                status="OFFERED",
                is_eligible=1
            )
            db.add(app)
            db.flush()
        else:
            app.status = "OFFERED"

        # 4. Map frontend status to database enum
        db_status = map_frontend_status_to_db(data.status)

        # 5. Check if offer already exists for this application
        existing_offer = db.query(PlacementOffer).filter(PlacementOffer.application_id == app.application_id).first()
        if existing_offer:
            return returnException("An offer is already issued to this student for the selected drive. Use Edit/Update instead.")

        # 6. Create the offer
        issued_datetime = datetime.combine(data.offer_date, datetime.min.time()) if data.offer_date else datetime.now()
        
        decline_reason = data.remarks if db_status == "DECLINED" else None
        revoke_reason = data.remarks if db_status == "REVOKED" else None

        new_offer = PlacementOffer(
            tenant_id=org_id,
            application_id=app.application_id,
            drive_id=data.drive_id,
            profile_id=profile.profile_id,
            ctc=data.package_ctc,
            role=data.designation,
            location=data.location,
            joining_date=data.joining_date,
            offer_letter_path=data.offer_letter_path,
            is_ppo=0,
            status=db_status,
            issued_at=issued_datetime,
            decline_reason=decline_reason,
            revoke_reason=revoke_reason,
            generated_from_template=0,
        )

        if db_status == "ACCEPTED":
            new_offer.accepted_at = datetime.now()
        elif db_status == "DECLINED":
            new_offer.declined_at = datetime.now()
        elif db_status == "REVOKED":
            new_offer.revoked_at = datetime.now()

        db.add(new_offer)
        db.flush() # Populate offer_id

        # 7. Apply locking policy
        user_id = current_user.get("user_id", 1)
        handle_offer_status_change(db, profile.profile_id, "NONE", db_status, org_id, new_offer.offer_id, recorded_by=user_id)

        db.commit()
        return returnSuccess("Offer created successfully.")
    except Exception as e:
        db.rollback()
        return returnException(str(e))


@router.put("/update/{id}")
def update_offer(
    id: int,
    data: OfferUpdateSchema,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        offer = db.query(PlacementOffer).filter(
            PlacementOffer.offer_id == id, 
            PlacementOffer.tenant_id == org_id
        ).first()

        if not offer:
            return returnException("Offer record not found.")

        # Save old status for transition tracking
        old_status = offer.status
        new_status = map_frontend_status_to_db(data.status)

        # Update details
        if offer.joining_date != data.joining_date:
            if data.joining_date <= date.today():
                return returnException("Joining Date must be a future date.")

        offer.ctc = data.package_ctc
        offer.role = data.designation
        offer.location = data.location
        offer.joining_date = data.joining_date
        offer.status = new_status
        
        if data.offer_letter_path:
            offer.offer_letter_path = data.offer_letter_path

        # Update timestamps
        if old_status != "ACCEPTED" and new_status == "ACCEPTED":
            offer.accepted_at = datetime.now()
        elif old_status != "DECLINED" and new_status == "DECLINED":
            offer.declined_at = datetime.now()
            offer.decline_reason = data.remarks
        elif old_status != "REVOKED" and new_status == "REVOKED":
            offer.revoked_at = datetime.now()
            offer.revoke_reason = data.remarks

        # Apply locking policy
        user_id = current_user.get("user_id", 1)
        handle_offer_status_change(db, offer.profile_id, old_status, new_status, org_id, offer.offer_id, recorded_by=user_id)

        db.commit()
        return returnSuccess("Offer updated successfully.")
    except Exception as e:
        db.rollback()
        return returnException(str(e))


@router.delete("/delete/{id}")
def delete_offer(
    id: int,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        offer = db.query(PlacementOffer).filter(
            PlacementOffer.offer_id == id,
            PlacementOffer.tenant_id == org_id
        ).first()

        if not offer:
            return returnException("Offer not found.")

        old_status = offer.status
        profile_id = offer.profile_id
        app_id = offer.application_id

        # Delete any child records in plm_post_placement first
        from sqlalchemy import text
        db.execute(
            text(f"DELETE FROM plm_post_placement WHERE offer_id = {id}")
        )

        # Delete offer
        db.delete(offer)

        # Revert locking status (effectively transition from ACCEPTED -> NONE if it was accepted)
        handle_offer_status_change(db, profile_id, old_status, "NONE", org_id)

        # Reset application status to SHORTLISTED or IN_PROCESS
        app = db.query(PlacementApplication).filter(PlacementApplication.application_id == app_id).first()
        if app:
            app.status = "SHORTLISTED"

        db.commit()
        return returnSuccess("Offer record deleted successfully.")
    except Exception as e:
        db.rollback()
        return returnException(str(e))


@router.get("/passed-students/{drive_id}")
def get_passed_students_for_drive(
    drive_id: int,
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        results = (
            db.query(
                IEMStudents.student_id,
                IEMStudents.name,
                IEMStudents.usno,
                PLMStudentProfile.profile_id
            )
            .join(PLMStudentProfile, PLMStudentProfile.student_id == IEMStudents.student_id)
            .join(PlacementApplication, PlacementApplication.profile_id == PLMStudentProfile.profile_id)
            .filter(
                PlacementApplication.drive_id == drive_id,
                PlacementApplication.status.in_(["SHORTLISTED", "OFFERED"]),
                PlacementApplication.tenant_id == org_id
            )
            .all()
        )

        students_list = []
        for r in results:
            students_list.append({
                "student_id": r.student_id,
                "name": r.name,
                "usno": r.usno or "",
                "profile_id": r.profile_id
            })

        return returnSuccess(students_list)
    except Exception as e:
        return returnException(str(e))


# --- PDF Offer Letter Generation API ---

@router.get("/generate-letter/{id}")
def generate_offer_letter(
    id: int,
    db: Session = Depends(get_db),
):
    try:
        offer = db.query(PlacementOffer).filter(PlacementOffer.offer_id == id).first()
        if not offer:
            raise HTTPException(status_code=404, detail="Offer record not found.")

        if offer.status != "Accepted":
            raise HTTPException(
                status_code=400,
                detail="Offer letter can only be downloaded after the candidate accepts the offer."
            )

        drive = db.query(PlacementDrive).filter(PlacementDrive.drive_id == offer.drive_id).first()
        company = db.query(PlacementCompany).filter(PlacementCompany.company_id == drive.company_id).first()
        profile = db.query(PLMStudentProfile).filter(PLMStudentProfile.profile_id == offer.profile_id).first()
        student = db.query(IEMStudents).filter(IEMStudents.student_id == profile.student_id).first()

        if not student or not company or not drive:
            raise HTTPException(status_code=404, detail="Related student or company data not found.")

        # Generate reportlab document in-memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=54,
            leftMargin=54,
            topMargin=54,
            bottomMargin=54
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            textColor=colors.HexColor('#1A365D'),
            alignment=1, # Center
            spaceAfter=5
        )

        subtitle_style = ParagraphStyle(
            'DocSub',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=15,
            textColor=colors.HexColor('#4A5568'),
            alignment=1, # Center
            spaceAfter=25
        )

        body_style = ParagraphStyle(
            'DocBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14.5,
            textColor=colors.HexColor('#2D3748'),
            spaceAfter=12
        )

        bold_body_style = ParagraphStyle(
            'DocBodyBold',
            parent=body_style,
            fontName='Helvetica-Bold'
        )

        heading_style = ParagraphStyle(
            'DocHeading',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=15,
            textColor=colors.HexColor('#1A365D'),
            spaceAfter=8,
            spaceBefore=12
        )

        story = []

        # Document Header
        story.append(Paragraph("IONCUDOS ERP - PLACEMENT DIVISION", title_style))
        story.append(Paragraph("CAMPUS RECRUITMENT CELL OFFER LETTER", subtitle_style))
        story.append(Spacer(1, 10))

        # Metadata
        curr_date = datetime.now().strftime("%d %B, %Y")
        story.append(Paragraph(f"<b>Date of Issue:</b> {curr_date}", body_style))
        story.append(Paragraph(f"<b>Reference ID:</b> PLM-OFF-{offer.offer_id:04d}", body_style))
        story.append(Spacer(1, 10))

        # Addressee
        story.append(Paragraph(f"To,<br/><b>{student.name}</b><br/>USN: {student.usno or student.regno or 'N/A'}<br/>Placement Profile ID: {offer.profile_id}", body_style))
        story.append(Spacer(1, 10))

        # Greeting & Opening
        story.append(Paragraph(f"Dear {student.name},", body_style))
        story.append(Paragraph(
            f"We are extremely pleased to issue this placement offer letter on behalf of <b>{company.company_name}</b>. "
            f"Following your outstanding performance in the recruitment rounds of the campus drive, the company has offered you "
            f"the position of <b>{offer.role}</b>.",
            body_style
        ))

        # Details Table
        table_data = [
            [Paragraph("<b>Parameter</b>", bold_body_style), Paragraph("<b>Details</b>", bold_body_style)],
            [Paragraph("Employer Name", body_style), Paragraph(company.company_name, body_style)],
            [Paragraph("Designation / Role", body_style), Paragraph(offer.role, body_style)],
            [Paragraph("Compensation (CTC)", body_style), Paragraph(f"{offer.ctc} LPA", body_style)],
            [Paragraph("Job Location", body_style), Paragraph(offer.location or "To Be Announced", body_style)],
            [Paragraph("Proposed Joining Date", body_style), Paragraph(offer.joining_date.strftime("%d %B, %Y") if offer.joining_date else "To Be Announced", body_style)],
            [Paragraph("Offer Status", body_style), Paragraph(map_db_status_to_frontend(offer.status, bool(offer.generated_from_template)), body_style)]
        ]

        table = Table(table_data, colWidths=[2.5*inch, 4.0*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (1,0), colors.HexColor('#EDF2F7')),
            ('TEXTCOLOR', (0,0), (1,0), colors.HexColor('#1A365D')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ]))

        story.append(table)
        story.append(Spacer(1, 15))

        # Terms
        story.append(Paragraph("Placement Rules & Conditions:", heading_style))
        story.append(Paragraph("1. This offer is valid subject to student maintaining academic eligibility and completing the graduation program with no active backlogs.", body_style))
        story.append(Paragraph("2. A formal onboarding contract containing detailed salary break-ups, employee benefits, and joining formalities will be sent directly by the company HR.", body_style))
        story.append(Paragraph("3. <b>Locking Policy:</b> By accepting this campus offer, you will be locked from participating in other placement drives, in compliance with the institution placement policy.", body_style))
        story.append(Spacer(1, 20))

        # Signatures
        sig_data = [
            [Paragraph("<b>For Institution Placement Cell</b>", body_style), Paragraph("<b>Candidate Acknowledgment</b>", body_style)],
            [Spacer(1, 35), Spacer(1, 35)],
            [Paragraph("_____________________________<br/><b>Placement Officer (TPO)</b>", body_style), Paragraph("_____________________________<br/><b>Student Signature & Date</b>", body_style)]
        ]
        sig_table = Table(sig_data, colWidths=[3.25*inch, 3.25*inch])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ]))
        story.append(sig_table)

        doc.build(story)
        pdf_content = buffer.getvalue()
        buffer.close()

        # Return as streaming response
        return StreamingResponse(
            BytesIO(pdf_content),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Offer_Letter_{student.name.replace(' ', '_')}.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PostPlacementSaveSchema(BaseModel):
    offer_id: int
    joining_confirmation_date: Optional[date] = None
    actual_joining_date: Optional[date] = None
    status: str
    no_show_reason: Optional[str] = None
    deferral_date: Optional[date] = None


@router.get("/post-placement/list")
def list_post_placement(
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        results = (
            db.query(
                PlacementOffer.offer_id,
                PlacementOffer.role,
                PlacementOffer.ctc,
                PlacementOffer.joining_date.label("proposed_joining_date"),
                PlacementCompany.company_name,
                PlacementDrive.drive_name,
                IEMStudents.name.label("student_name"),
                IEMStudents.usno.label("usn"),
                PlacementPostPlacement.pp_id,
                PlacementPostPlacement.joining_confirmation_date,
                PlacementPostPlacement.actual_joining_date,
                PlacementPostPlacement.status.label("post_placement_status"),
                PlacementPostPlacement.no_show_reason,
                PlacementPostPlacement.deferral_date,
            )
            .join(PlacementDrive, PlacementDrive.drive_id == PlacementOffer.drive_id)
            .join(PlacementCompany, PlacementCompany.company_id == PlacementDrive.company_id)
            .join(PLMStudentProfile, PLMStudentProfile.profile_id == PlacementOffer.profile_id)
            .join(IEMStudents, IEMStudents.student_id == PLMStudentProfile.student_id)
            .outerjoin(PlacementPostPlacement, PlacementPostPlacement.offer_id == PlacementOffer.offer_id)
            .filter(PlacementOffer.status == "ACCEPTED")
            .filter(PlacementOffer.tenant_id == org_id)
            .all()
        )

        tracking_list = []
        for r in results:
            tracking_list.append({
                "offer_id": r.offer_id,
                "student_name": r.student_name,
                "usn": r.usn,
                "company_name": r.company_name,
                "drive_name": r.drive_name,
                "designation": r.role,
                "package_ctc": str(r.ctc) if r.ctc else "0.0",
                "proposed_joining_date": str(r.proposed_joining_date) if r.proposed_joining_date else None,
                "pp_id": r.pp_id,
                "joining_confirmation_date": str(r.joining_confirmation_date) if r.joining_confirmation_date else None,
                "actual_joining_date": str(r.actual_joining_date) if r.actual_joining_date else None,
                "status": r.post_placement_status or "CONFIRMED",
                "no_show_reason": r.no_show_reason or "",
                "deferral_date": str(r.deferral_date) if r.deferral_date else None,
            })

        return returnSuccess(tracking_list)
    except Exception as e:
        return returnException(str(e))


@router.post("/post-placement/save")
def save_post_placement(
    data: PostPlacementSaveSchema,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id", 1)

        # 1. Resolve offer
        offer = db.query(PlacementOffer).filter(
            PlacementOffer.offer_id == data.offer_id,
            PlacementOffer.tenant_id == org_id
        ).first()

        if not offer:
            return returnException("Placement offer not found.")

        # 2. Find or create post-placement record
        record = db.query(PlacementPostPlacement).filter(
            PlacementPostPlacement.offer_id == data.offer_id
        ).first()

        if not record:
            record = PlacementPostPlacement(
                offer_id=data.offer_id,
                joining_confirmation_date=data.joining_confirmation_date,
                actual_joining_date=data.actual_joining_date,
                status=data.status,
                no_show_reason=data.no_show_reason,
                deferral_date=data.deferral_date,
                recorded_by=user_id,
                recorded_at=datetime.now()
            )
            db.add(record)
        else:
            record.joining_confirmation_date = data.joining_confirmation_date
            record.actual_joining_date = data.actual_joining_date
            record.status = data.status
            record.no_show_reason = data.no_show_reason
            record.deferral_date = data.deferral_date
            record.recorded_by = user_id
            record.recorded_at = datetime.now()

        # 3. If onboarding status is REVOKED, update the offer status & apply locking policy to unlock
        if data.status == "REVOKED":
            old_status = offer.status
            offer.status = "REVOKED"
            offer.revoked_at = datetime.now()
            offer.revoke_reason = data.no_show_reason or "Revoked during onboarding"
            
            # Apply locking policy to unlock student
            handle_offer_status_change(db, offer.profile_id, old_status, "REVOKED", org_id, offer.offer_id)

        db.commit()
        return returnSuccess("Onboarding status updated successfully.")
    except Exception as e:
        db.rollback()
        return returnException(str(e))


class StudentStatusChangeSchema(BaseModel):
    offer_id: int
    status: str
    remarks: Optional[str] = None


@router.get("/student/my-offers")
def get_student_offers(
    student_id: int,
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        profile = db.query(PLMStudentProfile).filter(
            PLMStudentProfile.student_id == student_id,
            PLMStudentProfile.org_id == org_id
        ).first()

        if not profile:
            return returnSuccess([])

        results = (
            db.query(
                PlacementOffer.offer_id,
                PlacementOffer.ctc,
                PlacementOffer.role,
                PlacementOffer.location,
                PlacementOffer.joining_date,
                PlacementOffer.offer_letter_path,
                PlacementOffer.status,
                PlacementOffer.issued_at,
                PlacementOffer.generated_from_template,
                PlacementDrive.drive_name,
                PlacementCompany.company_name
            )
            .join(PlacementDrive, PlacementDrive.drive_id == PlacementOffer.drive_id)
            .join(PlacementCompany, PlacementCompany.company_id == PlacementDrive.company_id)
            .filter(
                PlacementOffer.profile_id == profile.profile_id,
                PlacementOffer.tenant_id == org_id
            )
            .all()
        )

        offers_list = []
        for r in results:
            offers_list.append({
                "id": r.offer_id,
                "company_name": r.company_name,
                "drive_name": r.drive_name,
                "designation": r.role,
                "package_ctc": str(r.ctc) if r.ctc else "0.0",
                "location": r.location or "N/A",
                "offer_date": str(r.issued_at.date()) if r.issued_at else None,
                "joining_date": str(r.joining_date) if r.joining_date else None,
                "status": map_db_status_to_frontend(r.status, bool(r.generated_from_template))
            })

        return returnSuccess(offers_list)
    except Exception as e:
        return returnException(str(e))


@router.post("/student/respond")
def student_respond_to_offer(
    data: StudentStatusChangeSchema,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        offer = db.query(PlacementOffer).filter(
            PlacementOffer.offer_id == data.offer_id,
            PlacementOffer.tenant_id == org_id
        ).first()

        if not offer:
            return returnException("Offer record not found.")

        old_status = offer.status
        new_status = map_frontend_status_to_db(data.status)

        offer.status = new_status
        if new_status == "ACCEPTED":
            offer.accepted_at = datetime.now()
        elif new_status == "DECLINED":
            offer.declined_at = datetime.now()
            offer.decline_reason = data.remarks

        user_id = current_user.get("user_id", 1)
        handle_offer_status_change(db, offer.profile_id, old_status, new_status, org_id, offer.offer_id, recorded_by=user_id)

        db.commit()
        return returnSuccess("Response submitted successfully.")
    except Exception as e:
        db.rollback()
        return returnException(str(e))
