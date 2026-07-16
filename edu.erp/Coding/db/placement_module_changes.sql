---shrikant 22/06/2026
ALTER TABLE plm_drive
ADD COLUMN vacancy_count SMALLINT(5) DEFAULT NULL;

-- =========================================================================
-- SECTION 2: MASTER DATA FIXES
-- Required so all departments and batch years appear in Drive creation form.
-- Safe to run multiple times — only updates rows where org_id IS NULL.
-- =========================================================================

-- Fix branches (departments) not showing in Eligible Branches dropdown
UPDATE iems_department
SET org_id = 1
WHERE org_id IS NULL AND status = 1;

-- Fix batch years not showing in Eligible Batch Years dropdown
UPDATE iems_academic_batch
SET org_id = 1
WHERE org_id IS NULL AND status = 1;

-- =========================================================================
-- SECTION 3: SAMPLE DATA — Company Self-Registration
-- 5 sample companies for testing the TPO Company Approval workflow.
-- Status: 0 = Pending, 1 = Approved, 2 = Rejected
-- =========================================================================

INSERT INTO `plm_company_self_registration`
  (`company_name`, `company_type`, `industry`, `website`, `email`, `phone`,
   `address`, `city`, `state`, `country`, `pincode`,
   `contact_person`, `contact_email`, `contact_phone`,
   `description`, `status`, `org_id`, `create_date`)
VALUES
  -- 1. Pending
  ('Infosys Limited', 'Private', 'Information Technology',
   'https://www.infosys.com', 'campus@infosys.com', '9845001234',
   'Electronics City, Phase 1', 'Bengaluru', 'Karnataka', 'India', '560100',
   'Rahul Mehta', 'rahul.mehta@infosys.com', '9845001234',
   'Global leader in IT services and consulting with 300,000+ employees worldwide.',
   0, 1, NOW()),

  -- 2. Pending
  ('Wipro Technologies', 'Private', 'Information Technology',
   'https://www.wipro.com', 'hr.campus@wipro.com', '9900112233',
   'Sarjapur Road, Outer Ring Road', 'Bengaluru', 'Karnataka', 'India', '560035',
   'Sneha Reddy', 'sneha.reddy@wipro.com', '9900112233',
   'Leading global IT, consulting and business process services company.',
   0, 1, NOW()),

  -- 3. Pending
  ('Tata Consultancy Services', 'Private', 'Information Technology',
   'https://www.tcs.com', 'campus.hiring@tcs.com', '9876543210',
   'TCS House, Raveline Street', 'Mumbai', 'Maharashtra', 'India', '400001',
   'Anil Kumar', 'anil.kumar@tcs.com', '9876543210',
   'Largest IT services company in India with global presence in 46 countries.',
   0, 1, NOW()),

  -- 4. Approved (company_id left NULL; TPO approve action will fill it)
  ('HCL Technologies', 'Private', 'Information Technology',
   'https://www.hcltech.com', 'talent@hcl.com', '9988776655',
   'Plot No. 3A, Sector 126', 'Noida', 'Uttar Pradesh', 'India', '201304',
   'Priya Sharma', 'priya.sharma@hcl.com', '9988776655',
   'Technology company with expertise in digital, engineering and cloud services.',
   1, 1, DATE_SUB(NOW(), INTERVAL 5 DAY)),

  -- 5. Rejected
  ('XYZ Fake Solutions', 'Private', 'Consulting',
   'https://www.xyzfake.com', 'contact@xyzfake.com', '9000000001',
   '123 Ghost Road', 'Hyderabad', 'Telangana', 'India', '500001',
   'Unknown Person', 'unknown@xyzfake.com', '9000000001',
   'Unverified company with no verifiable website or registration details.',
   2, 1, DATE_SUB(NOW(), INTERVAL 10 DAY));

-- =========================================================================
-- SECTION 4: INCREMENTAL CHANGES — Company Contact Refactoring
-- Replaced iems_company_contact with plm_company_contact.
-- Aligned fields to name (VARCHAR), designation (VARCHAR), is_active (TINYINT).
-- =========================================================================

-- Rename the table if it was named iems_company_contact
RENAME TABLE iems_company_contact TO plm_company_contact;

-- Drop first_name and last_name and add name column
ALTER TABLE plm_company_contact
DROP COLUMN first_name,
DROP COLUMN last_name,
ADD COLUMN name VARCHAR(150) NOT NULL AFTER company_id;

-- Modify designation column type to VARCHAR
ALTER TABLE plm_company_contact
MODIFY COLUMN designation VARCHAR(100) DEFAULT NULL;

-- Add is_active column
ALTER TABLE plm_company_contact
ADD COLUMN is_active TINYINT(1) DEFAULT 1;

-- Add company_type column to plm_company if it does not exist
DROP PROCEDURE IF EXISTS AddCompanyTypeColumn;
DELIMITER //
CREATE PROCEDURE AddCompanyTypeColumn()
BEGIN
    IF NOT EXISTS(
        SELECT * FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'plm_company'
        AND COLUMN_NAME = 'company_type'
    ) THEN
        ALTER TABLE plm_company ADD COLUMN company_type VARCHAR(100) DEFAULT NULL AFTER company_name;
    END IF;
END //
DELIMITER ;
CALL AddCompanyTypeColumn();
DROP PROCEDURE IF EXISTS AddCompanyTypeColumn;


-- =========================================================================
-- SECTION 5: INTERVIEW MODULE TABLES
-- Added by: Interview Schedule Feature — 09/07/2026
-- Safe to re-run: uses CREATE TABLE IF NOT EXISTS
-- Tables: plm_interview_schedule, plm_interview_slot,
--         plm_round_result, plm_org_holiday
-- =========================================================================

-- -----------------------------------------------------------------------------
-- 5.1 plm_interview_schedule
--     One schedule per round per drive.
--     UNIQUE KEY prevents duplicate active schedules for the same round.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS plm_interview_schedule (
    schedule_id       INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    drive_id          INT           NOT NULL,            -- FK → plm_drive.drive_id
    round_id          INT           NOT NULL,            -- FK → plm_drive_round.round_id
    org_id            INT           NOT NULL DEFAULT 1,

    -- Venue
    venue_type        VARCHAR(10)   NOT NULL DEFAULT 'PHYSICAL',  -- PHYSICAL | VIRTUAL
    venue_details     VARCHAR(500)  NULL,
    meeting_link      VARCHAR(500)  NULL,

    -- Timing
    scheduled_date    DATE          NULL,               -- Start date
    end_date          DATE          NULL,               -- Last date (multi-day)
    start_time        VARCHAR(10)   NULL DEFAULT '09:00',
    end_time          VARCHAR(10)   NULL DEFAULT '17:00',
    status            VARCHAR(20)   NULL DEFAULT 'DRAFT',
    interviewer_email VARCHAR(500)  NULL,
    tenant_id         INT           NULL DEFAULT 1,

    -- Engine output (stored for quick display / stats)
    scheduling_mode   VARCHAR(30)   NOT NULL DEFAULT 'ALL_SEQUENTIAL',
    batch_size        SMALLINT      NULL,               -- students per batch (NULL for non-batch modes)
    total_students    INT           NOT NULL DEFAULT 0,
    total_slots       INT           NOT NULL DEFAULT 0,
    days_required     INT           NOT NULL DEFAULT 1,

    -- Interviewer (comma-separated for simplicity)
    interviewer_names VARCHAR(500)  NULL,

    is_active         TINYINT       NOT NULL DEFAULT 1, -- 0 = soft deleted
    created_by        INT           NULL,
    created_at        DATETIME      NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME      NULL ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (schedule_id),

    -- One active schedule per round per drive
    UNIQUE KEY uq_drive_round_active (drive_id, round_id, is_active),

    INDEX idx_sched_drive  (drive_id),
    INDEX idx_sched_round  (round_id),
    INDEX idx_sched_org    (org_id, is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- -----------------------------------------------------------------------------
-- 5.2 plm_interview_slot
--     One row per student per schedule.
--     batch_number stored as a column (not a separate table).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS plm_interview_slot (
    slot_id           INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    schedule_id       INT UNSIGNED  NOT NULL,            -- FK → plm_interview_schedule
    application_id    INT           NOT NULL,            -- FK → plm_application

    -- Timing (computed by frontend scheduleEngine, stored for display)
    slot_time         DATETIME      NULL,

    -- Batch grouping (NULL for non-batch modes)
    batch_number      SMALLINT      NULL,
    seq_number        SMALLINT      NULL,

    -- Interviewer override (optional)
    interviewer_name    VARCHAR(200)  NULL,
    interviewer_email   VARCHAR(150)  NULL,
    contact_id          INT           NULL,
    notification_status VARCHAR(20)   NULL,

    -- Slot status
    status            VARCHAR(20)   NOT NULL DEFAULT 'SCHEDULED',
    -- SCHEDULED | COMPLETED | ABSENT | CANCELLED

    PRIMARY KEY (slot_id),

    -- Prevent same student scheduled twice for same schedule
    UNIQUE KEY uq_slot_student (schedule_id, application_id),

    INDEX idx_slot_schedule  (schedule_id),
    INDEX idx_slot_app       (application_id),
    INDEX idx_slot_batch     (schedule_id, batch_number),
    INDEX idx_slot_time      (slot_time),

    CONSTRAINT fk_slot_schedule
        FOREIGN KEY (schedule_id)
        REFERENCES plm_interview_schedule (schedule_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_slot_contact
        FOREIGN KEY (contact_id)
        REFERENCES plm_company_contact (contact_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- -----------------------------------------------------------------------------
-- 5.3 plm_round_result
--     One result row per student per round.
--     UNIQUE KEY enables INSERT ... ON DUPLICATE KEY UPDATE (idempotent upsert).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS plm_round_result (
    result_id         INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    application_id    INT           NOT NULL,            -- FK → plm_application
    round_id          INT           NOT NULL,            -- FK → plm_drive_round

    result            VARCHAR(10)   NOT NULL,            -- PASS | FAIL | HOLD | ABSENT
    feedback_notes    TEXT          NULL,
    recorded_by       INT           NOT NULL DEFAULT 1,
    recorded_at       DATETIME      NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (result_id),

    UNIQUE KEY uq_application_round (application_id, round_id),

    INDEX idx_result_app         (application_id),
    INDEX idx_result_round       (round_id),
    INDEX idx_result_by_round_drive (round_id, result)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- -----------------------------------------------------------------------------
-- 5.4 plm_org_holiday
--     Calendar blocking for the scheduling wizard.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS plm_org_holiday (
    holiday_id        INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    holiday_date      DATE          NOT NULL,
    holiday_name      VARCHAR(150)  NOT NULL,
    holiday_type      VARCHAR(10)   NOT NULL DEFAULT 'PUBLIC',  -- PUBLIC | CUSTOM
    org_id            INT           NOT NULL DEFAULT 1,
    is_active         TINYINT       NOT NULL DEFAULT 1,
    created_by        INT           NULL,
    created_at        DATETIME      NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (holiday_id),
    UNIQUE KEY uq_holiday_date_org (holiday_date, org_id),
    INDEX idx_holiday_org_active (org_id, is_active, holiday_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- =========================================================================
-- SECTION 6: PLACEMENT DRIVES SEEDING
-- Creates 5 placement drives with realistic configurations (Vacancy, CTC, Eligibility, Status)
-- Links drives to branch constraints and adds selection round structures.
-- =========================================================================

-- ── 1. Google India SWE Drive 2025 (eligible: 42 CSE students)
INSERT INTO plm_drive (
  company_id, drive_name, job_role, vacancy_count, drive_type, work_type, location,
  ctc_min, ctc_max, job_description, min_cgpa, max_backlogs,
  application_start, application_deadline, drive_date, tier, status,
  eligible_student_count, applied_count, shortlisted_count, org_id, created_by
) VALUES (
  1, 'Google India SWE Drive 2025', 'Associate Software Engineer', 15, 'On-Campus', 'Hybrid', 'Bengaluru Office',
  18.00, 22.00, 'Work on core products, search engines, and infrastructure scale solutions.', 7.00, 0,
  '2026-07-10', '2026-07-20', '2026-07-25', 1, 2,
  42, 0, 0, 1, 1
);
SET @google_id = LAST_INSERT_ID();

INSERT INTO plm_drive_eligible_branch (drive_id, dept_id, batch_year) VALUES (@google_id, 71, 2021);

INSERT INTO plm_drive_round (drive_id, round_number, round_name, round_type, is_eliminatory, round_date, duration_minutes, description) VALUES
  (@google_id, 1, 'Online Technical Coding', 'TECHNICAL', 1, '2026-07-26', 60, 'Coding contest on DSA'),
  (@google_id, 2, 'Technical Interview 1', 'TECHNICAL', 1, '2026-07-27', 45, 'Algorithms and data structures'),
  (@google_id, 3, 'Technical Interview 2', 'TECHNICAL', 1, '2026-07-27', 45, 'System Design & Googliness'),
  (@google_id, 4, 'HR Interview', 'HR', 0, '2026-07-28', 30, 'Behavioral & Leadership interview');

-- ── 2. Microsoft SWE Placement Drive (eligible: 70 CSE/EC students)
INSERT INTO plm_drive (
  company_id, drive_name, job_role, vacancy_count, drive_type, work_type, location,
  ctc_min, ctc_max, job_description, min_cgpa, max_backlogs,
  application_start, application_deadline, drive_date, tier, status,
  eligible_student_count, applied_count, shortlisted_count, org_id, created_by
) VALUES (
  2, 'Microsoft SWE Placement Drive', 'Support Engineer', 20, 'On-Campus', 'Onsite', 'Hyderabad Campus',
  12.00, 16.00, 'Troubleshoot and develop patches for Windows and Azure enterprise clients.', 6.50, 0,
  '2026-07-10', '2026-07-20', '2026-07-26', 1, 2,
  70, 0, 0, 1, 1
);
SET @microsoft_id = LAST_INSERT_ID();

INSERT INTO plm_drive_eligible_branch (drive_id, dept_id, batch_year) VALUES 
  (@microsoft_id, 71, 2021),
  (@microsoft_id, 73, 2021);

INSERT INTO plm_drive_round (drive_id, round_number, round_name, round_type, is_eliminatory, round_date, duration_minutes, description) VALUES
  (@microsoft_id, 1, 'Online Assessment', 'APTITUDE', 1, '2026-07-27', 60, 'Analytical and logical reasoning questions'),
  (@microsoft_id, 2, 'Technical Round', 'TECHNICAL', 1, '2026-07-28', 45, 'Data structures & problem solving'),
  (@microsoft_id, 3, 'HR Round', 'HR', 0, '2026-07-29', 30, 'Fitment and career aspiration checks');

-- ── 3. Amazon Cloud Support Associate Drive (eligible: 100 CSE/EC/ME students)
INSERT INTO plm_drive (
  company_id, drive_name, job_role, vacancy_count, drive_type, work_type, location,
  ctc_min, ctc_max, job_description, min_cgpa, max_backlogs,
  application_start, application_deadline, drive_date, tier, status,
  eligible_student_count, applied_count, shortlisted_count, org_id, created_by
) VALUES (
  3, 'Amazon Cloud Support Associate Drive', 'Cloud Support Associate', 35, 'On-Campus', 'Remote', 'Bengaluru Office',
  8.50, 11.00, 'Help enterprise customers manage, optimize, and secure their AWS cloud workloads.', 6.00, 1,
  '2026-07-10', '2026-07-20', '2026-07-27', 1, 2,
  100, 0, 0, 1, 1
);
SET @amazon_id = LAST_INSERT_ID();

INSERT INTO plm_drive_eligible_branch (drive_id, dept_id, batch_year) VALUES 
  (@amazon_id, 71, 2021),
  (@amazon_id, 73, 2021),
  (@amazon_id, 79, 2021);

INSERT INTO plm_drive_round (drive_id, round_number, round_name, round_type, is_eliminatory, round_date, duration_minutes, description) VALUES
  (@amazon_id, 1, 'Written Test', 'APTITUDE', 1, '2026-07-28', 60, 'AWS core and basic troubleshooting Aptitude'),
  (@amazon_id, 2, 'Technical Interview', 'TECHNICAL', 1, '2026-07-29', 60, 'Operating systems & networking concepts'),
  (@amazon_id, 3, 'HR Interview', 'HR', 0, '2026-07-30', 30, 'Amazon Leadership Principles evaluation');

-- ── 4. Create Accenture ASE Drive (eligible: 70 CSE/EC students)
INSERT INTO plm_drive (
  company_id, drive_name, job_role, vacancy_count, drive_type, work_type, location,
  ctc_min, ctc_max, job_description, min_cgpa, max_backlogs,
  application_start, application_deadline, drive_date, tier, status,
  eligible_student_count, applied_count, shortlisted_count, org_id, created_by
) VALUES (
  4, 'Accenture ASE Drive', 'Associate Software Engineer', 50, 'Pool Campus', 'Onsite', 'VVCE Campus',
  4.50, 6.50, 'General software development, maintenance, and client operations support.', 5.50, 2,
  '2026-07-10', '2026-07-20', '2026-07-28', 2, 2,
  70, 0, 0, 1, 1
);
SET @accenture_id = LAST_INSERT_ID();

INSERT INTO plm_drive_eligible_branch (drive_id, dept_id, batch_year) VALUES 
  (@accenture_id, 71, 2021),
  (@accenture_id, 73, 2021);

INSERT INTO plm_drive_round (drive_id, round_number, round_name, round_type, is_eliminatory, round_date, duration_minutes, description) VALUES
  (@accenture_id, 1, 'Cognitive & Technical Assessment', 'APTITUDE', 1, '2026-07-29', 90, 'Reasoning, english, and basic tech MCQs'),
  (@accenture_id, 2, 'Communication Test', 'OTHER', 0, '2026-07-29', 30, 'Spoken english, grammar, and listening check'),
  (@accenture_id, 3, 'Technical & HR', 'TECHNICAL', 0, '2026-07-30', 30, 'Review of resume projects and behavioral check');

-- ── 5. Create NVIDIA Hardware Engineer Drive (eligible: 28 EC students)
INSERT INTO plm_drive (
  company_id, drive_name, job_role, vacancy_count, drive_type, work_type, location,
  ctc_min, ctc_max, job_description, min_cgpa, max_backlogs,
  application_start, application_deadline, drive_date, tier, status,
  eligible_student_count, applied_count, shortlisted_count, org_id, created_by
) VALUES (
  5, 'NVIDIA Hardware Engineer Drive', 'ASIC Design Engineer', 8, 'On-Campus', 'Hybrid', 'Bengaluru Office',
  15.00, 18.00, 'Design next-gen high speed GPU architectures using Verilog/VHDL.', 7.50, 0,
  '2026-07-10', '2026-07-20', '2026-07-29', 1, 2,
  28, 0, 0, 1, 1
);
SET @nvidia_id = LAST_INSERT_ID();

INSERT INTO plm_drive_eligible_branch (drive_id, dept_id, batch_year) VALUES 
  (@nvidia_id, 73, 2021);

INSERT INTO plm_drive_round (drive_id, round_number, round_name, round_type, is_eliminatory, round_date, duration_minutes, description) VALUES
  (@nvidia_id, 1, 'Technical Written', 'TECHNICAL', 1, '2026-07-30', 90, 'Digital electronics and microprocessors test'),
  (@nvidia_id, 2, 'Interview Round 1', 'TECHNICAL', 1, '2026-07-31', 60, 'Verilog, CMOS logic design review'),
  (@nvidia_id, 3, 'Interview Round 2', 'TECHNICAL', 1, '2026-07-31', 45, 'Deep dive into computer architecture');


-- =============================================================================
-- SECTION 7: FEATURE ENHANCEMENTS — Interview Scheduling Module
-- Date: 2026-07-11
-- Author: Merged from temp_phase1_migration.sql
-- Features: F2 (interviewer_id, student_id), F4 (notification_sent_at),
--           F5 (notification_expires_at), F6 (profile_status)
-- Safe: All new columns are nullable — existing rows unaffected.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 7.1  plm_interview_slot — New columns
--      F2: interviewer_id  → will FK to plm_company_contact (after Feature 1 fix)
--      F2: student_id      → denormalised FK to iems_students for fast lookup
--      F4: notification_sent_at → tracks when student was notified for this slot
--      F5: notification_expires_at → set = slot_time (expires at interview start)
-- -----------------------------------------------------------------------------
ALTER TABLE plm_interview_slot
    ADD COLUMN interviewer_id          INT           NULL
        COMMENT 'FK to plm_company_contact.contact_id (linked after Feature 1 fix)',

    ADD COLUMN student_id              INT           NULL
        COMMENT 'FK to iems_students.student_id (denormalised for fast lookup)',

    ADD COLUMN notification_sent_at    DATETIME      NULL
        COMMENT 'Timestamp when interview notification was sent to this student',

    ADD COLUMN notification_expires_at DATETIME      NULL
        COMMENT 'Equals slot_time — notification considered expired at interview start',

    ADD INDEX idx_slot_interviewer (interviewer_id),
    ADD INDEX idx_slot_student     (student_id),
    ADD INDEX idx_slot_notif_sent  (notification_sent_at);

-- -----------------------------------------------------------------------------
-- 7.2  plm_notification_log — New columns
--      F5: expires_at     → copy of slot_time captured at send time (audit trail)
--      F6: profile_status → student's placement_status at moment of notification
-- -----------------------------------------------------------------------------
ALTER TABLE plm_notification_log
    ADD COLUMN expires_at      DATETIME      NULL
        COMMENT 'Notification expiry — copied from slot_time at send time',

    ADD COLUMN profile_status  VARCHAR(30)   NULL
        COMMENT 'plm_student_profile.placement_status at notification time: UNPLACED | APPLIED | IN_PROCESS | PLACED | OPTED_OUT';


-- =============================================================================
-- SECTION 8: CONTACT INTERVIEWER FLAG
-- Date: 2026-07-15
-- Adds is_interviewer flag to plm_company_contact so the schedule wizard
-- only shows contacts who are marked as interviewers, not all contacts.
-- Safe: nullable with DEFAULT 0, no existing rows affected.
-- =============================================================================

ALTER TABLE plm_company_contact
    ADD COLUMN is_interviewer TINYINT NOT NULL DEFAULT 0
        COMMENT '1 = this contact can be assigned as an interviewer in schedule wizard'
    AFTER is_primary;
