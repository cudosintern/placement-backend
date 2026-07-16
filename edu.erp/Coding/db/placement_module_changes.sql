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
