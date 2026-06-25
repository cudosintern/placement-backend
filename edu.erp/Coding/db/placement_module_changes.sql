---shrikant 22/06/2026
ALTER TABLE plm_drive
ADD COLUMN vacancy_count SMALLINT(5) DEFAULT NULL;

-- =========================================================================
-- SECTION 1: INITIAL SCHEMA CREATION FOR PLACEMENT MODULE (plm_)
-- Added by friend's script --- 25/06/2026
-- =========================================================================

CREATE TABLE IF NOT EXISTS `plm_company` (
  `company_id` INT NOT NULL AUTO_INCREMENT,
  `company_name` VARCHAR(200) NOT NULL,
  `company_type` VARCHAR(100) DEFAULT NULL,
  `industry` VARCHAR(100) DEFAULT NULL,

  `website` VARCHAR(255) DEFAULT NULL,
  `email` VARCHAR(150) DEFAULT NULL,
  `phone` VARCHAR(20) DEFAULT NULL,
  `address` TEXT DEFAULT NULL,
  `city` VARCHAR(100) DEFAULT NULL,
  `state` VARCHAR(100) DEFAULT NULL,
  `country` VARCHAR(100) DEFAULT 'India',
  `pincode` VARCHAR(10) DEFAULT NULL,
  `contact_person` VARCHAR(150) DEFAULT NULL,
  `contact_designation` VARCHAR(100) DEFAULT NULL,
  `contact_phone` VARCHAR(20) DEFAULT NULL,
  `contact_email` VARCHAR(150) DEFAULT NULL,
  `description` TEXT DEFAULT NULL,
  `logo_path` VARCHAR(500) DEFAULT NULL,
  `status` SMALLINT NOT NULL DEFAULT 1,
  `org_id` INT NOT NULL DEFAULT 1,
  `created_by` INT DEFAULT NULL,
  `modified_by` INT DEFAULT NULL,
  `create_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `modify_date` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS `plm_company_self_registration` (
  `reg_id` INT NOT NULL AUTO_INCREMENT,
  `company_id` INT DEFAULT NULL,
  `company_name` VARCHAR(200) NOT NULL,
  `company_type` VARCHAR(100) DEFAULT NULL,
  `industry` VARCHAR(100) DEFAULT NULL,
  `website` VARCHAR(255) DEFAULT NULL,
  `email` VARCHAR(150) DEFAULT NULL,
  `phone` VARCHAR(20) DEFAULT NULL,
  `address` TEXT DEFAULT NULL,
  `city` VARCHAR(100) DEFAULT NULL,
  `state` VARCHAR(100) DEFAULT NULL,
  `country` VARCHAR(100) DEFAULT 'India',
  `pincode` VARCHAR(10) DEFAULT NULL,
  `contact_person` VARCHAR(150) DEFAULT NULL,
  `contact_email` VARCHAR(150) DEFAULT NULL,
  `contact_phone` VARCHAR(20) DEFAULT NULL,
  `description` TEXT DEFAULT NULL,
  `status` SMALLINT NOT NULL DEFAULT 0,
  `reviewed_by` INT DEFAULT NULL,
  `review_date` DATETIME DEFAULT NULL,
  `remarks` VARCHAR(500) DEFAULT NULL,
  `org_id` INT NOT NULL DEFAULT 1,
  `submitted_by` INT DEFAULT NULL,
  `create_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `modify_date` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`reg_id`),
  KEY `fk_plm_registration_company` (`company_id`),
  CONSTRAINT `fk_plm_registration_company` FOREIGN KEY (`company_id`) REFERENCES `plm_company` (`company_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS `plm_drive` (
  `drive_id` INT NOT NULL AUTO_INCREMENT,
  `company_id` INT NOT NULL,
  `drive_name` VARCHAR(200) NOT NULL,
  `job_role` VARCHAR(150) NOT NULL,
  `drive_type` VARCHAR(50) NOT NULL DEFAULT 'On-Campus',
  `work_type` VARCHAR(50) NOT NULL DEFAULT 'Onsite',
  `location` VARCHAR(200) DEFAULT NULL,
  `ctc_min` DECIMAL(10,2) DEFAULT NULL,
  `ctc_max` DECIMAL(10,2) DEFAULT NULL,
  `job_description` TEXT DEFAULT NULL,
  `min_cgpa` DECIMAL(4,2) NOT NULL DEFAULT 0.00,
  `max_backlogs` SMALLINT NOT NULL DEFAULT 0,
  `application_start` DATE DEFAULT NULL,
  `application_deadline` DATE DEFAULT NULL,
  `drive_date` DATE DEFAULT NULL,
  `tier` SMALLINT NOT NULL DEFAULT 1,
  `status` SMALLINT NOT NULL DEFAULT 0,
  `eligible_student_count` INT NOT NULL DEFAULT 0,
  `applied_count` INT NOT NULL DEFAULT 0,
  `shortlisted_count` INT NOT NULL DEFAULT 0,
  `org_id` INT NOT NULL DEFAULT 1,
  `created_by` INT DEFAULT NULL,
  `modified_by` INT DEFAULT NULL,
  `create_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `modify_date` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`drive_id`),
  KEY `fk_plm_drive_company` (`company_id`),
  CONSTRAINT `fk_plm_drive_company` FOREIGN KEY (`company_id`) REFERENCES `plm_company` (`company_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS `plm_drive_eligible_branch` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `drive_id` INT NOT NULL,
  `dept_id` INT NOT NULL,
  `batch_year` SMALLINT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_plm_branch_drive` (`drive_id`),
  CONSTRAINT `fk_plm_branch_drive` FOREIGN KEY (`drive_id`) REFERENCES `plm_drive` (`drive_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS `plm_drive_round` (
  `round_id` INT NOT NULL AUTO_INCREMENT,
  `drive_id` INT NOT NULL,
  `round_number` SMALLINT NOT NULL,
  `round_name` VARCHAR(150) NOT NULL,
  `round_type` VARCHAR(50) NOT NULL,
  `is_eliminatory` SMALLINT NOT NULL DEFAULT 1,
  `round_date` DATE DEFAULT NULL,
  `duration_minutes` SMALLINT DEFAULT NULL,
  `description` TEXT DEFAULT NULL,
  PRIMARY KEY (`round_id`),
  KEY `fk_plm_round_drive` (`drive_id`),
  CONSTRAINT `fk_plm_round_drive` FOREIGN KEY (`drive_id`) REFERENCES `plm_drive` (`drive_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS `plm_student_profile` (
  `profile_id` INT NOT NULL AUTO_INCREMENT,
  `student_id` INT(10) UNSIGNED NOT NULL,
  `linkedin_url` VARCHAR(255) DEFAULT NULL,
  `github_url` VARCHAR(255) DEFAULT NULL,
  `portfolio_url` VARCHAR(255) DEFAULT NULL,
  `resume_path` VARCHAR(500) DEFAULT NULL,
  `current_cgpa` DECIMAL(4,2) DEFAULT NULL,
  `backlogs` INT DEFAULT 0,
  `is_placement_eligible` TINYINT DEFAULT 1,
  `career_objective` TEXT DEFAULT NULL,
  `preferred_locations` VARCHAR(255) DEFAULT NULL,
  `org_id` INT NOT NULL,
  `status` TINYINT DEFAULT 1,
  `created_by` INT DEFAULT NULL,
  `modified_by` INT DEFAULT NULL,
  `created_date` DATETIME DEFAULT NULL,
  `modified_date` DATETIME DEFAULT NULL,
  PRIMARY KEY (`profile_id`),
  UNIQUE KEY `uk_plm_student` (`student_id`),
  CONSTRAINT `fk_plm_profile_student` FOREIGN KEY (`student_id`) REFERENCES `iems_students` (`student_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS `plm_student_skill` (
  `skill_id` INT NOT NULL AUTO_INCREMENT,
  `profile_id` INT NOT NULL,
  `student_id` INT NOT NULL,
  `skill_name` VARCHAR(150) NOT NULL,
  `proficiency_level` VARCHAR(50) DEFAULT NULL,
  `org_id` INT NOT NULL,
  `status` TINYINT DEFAULT 1,
  `created_by` INT DEFAULT NULL,
  `modified_by` INT DEFAULT NULL,
  `created_date` DATETIME DEFAULT NULL,
  `modified_date` DATETIME DEFAULT NULL,
  PRIMARY KEY (`skill_id`),
  KEY `fk_plm_skill_profile` (`profile_id`),
  CONSTRAINT `fk_plm_skill_profile` FOREIGN KEY (`profile_id`) REFERENCES `plm_student_profile` (`profile_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS `plm_student_certification` (
  `certification_id` INT NOT NULL AUTO_INCREMENT,
  `profile_id` INT NOT NULL,
  `student_id` INT NOT NULL,
  `certification_name` VARCHAR(255) NOT NULL,
  `issuing_organization` VARCHAR(255) DEFAULT NULL,
  `issue_date` DATE DEFAULT NULL,
  `expiry_date` DATE DEFAULT NULL,
  `credential_id` VARCHAR(150) DEFAULT NULL,
  `credential_url` VARCHAR(500) DEFAULT NULL,
  `org_id` INT NOT NULL,
  `status` TINYINT DEFAULT 1,
  `created_by` INT DEFAULT NULL,
  `modified_by` INT DEFAULT NULL,
  `created_date` DATETIME DEFAULT NULL,
  `modified_date` DATETIME DEFAULT NULL,
  PRIMARY KEY (`certification_id`),
  KEY `fk_plm_cert_profile` (`profile_id`),
  CONSTRAINT `fk_plm_cert_profile` FOREIGN KEY (`profile_id`) REFERENCES `plm_student_profile` (`profile_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS `plm_student_resume` (
  `resume_id` INT NOT NULL AUTO_INCREMENT,
  `profile_id` INT NOT NULL,
  `student_id` INT NOT NULL,
  `file_name` VARCHAR(255) NOT NULL,
  `stored_name` VARCHAR(500) NOT NULL,
  `file_path` VARCHAR(1000) NOT NULL,
  `file_size_kb` INT DEFAULT NULL,
  `is_active` TINYINT DEFAULT 1,
  `org_id` INT NOT NULL,
  `status` TINYINT DEFAULT 1,
  `created_by` INT DEFAULT NULL,
  `modified_by` INT DEFAULT NULL,
  `created_date` DATETIME DEFAULT NULL,
  `modified_date` DATETIME DEFAULT NULL,
  PRIMARY KEY (`resume_id`),
  KEY `fk_plm_resume_profile` (`profile_id`),
  CONSTRAINT `fk_plm_resume_profile` FOREIGN KEY (`profile_id`) REFERENCES `plm_student_profile` (`profile_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Add vacancy_count to plm_drive if not already present (safe to run again)
ALTER TABLE plm_drive ADD COLUMN IF NOT EXISTS vacancy_count SMALLINT(5) DEFAULT NULL;

-- =========================================================================
-- SECTION 2: MASTER DATA FIXES
-- Required so all departments and batch years appear in Drive creation form.
-- The main DB dump imports these rows with org_id = NULL, which causes the
-- backend (filtered by org_id) to skip them entirely.
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
