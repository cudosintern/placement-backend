-- =========================================================================
-- SECTION 1: INITIAL SCHEMA CREATION FOR PLACEMENT MODULE (plm_)
-- =========================================================================

-- 1. Create plm_company table
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

-- 1.1 Create plm_company_contact table
CREATE TABLE IF NOT EXISTS `plm_company_contact` (
  `contact_id` INT NOT NULL AUTO_INCREMENT,
  `company_id` INT NOT NULL,
  `name` VARCHAR(150) NOT NULL,
  `designation` VARCHAR(100) DEFAULT NULL,
  `email` VARCHAR(150) DEFAULT NULL,
  `phone` VARCHAR(20) DEFAULT NULL,
  `is_primary` TINYINT(1) NOT NULL DEFAULT 0,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `create_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`contact_id`),
  KEY `fk_plm_contact_company` (`company_id`),
  CONSTRAINT `fk_plm_contact_company` FOREIGN KEY (`company_id`) REFERENCES `plm_company` (`company_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- 2. Create plm_company_self_registration table
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

-- 3. Create plm_drive table (Note: vacancy_count was added via Shrikant's ALTER patch below)
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

-- 4. Create plm_drive_eligible_branch table
CREATE TABLE IF NOT EXISTS `plm_drive_eligible_branch` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `drive_id` INT NOT NULL,
  `dept_id` INT NOT NULL,
  `batch_year` SMALLINT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_plm_branch_drive` (`drive_id`),
  CONSTRAINT `fk_plm_branch_drive` FOREIGN KEY (`drive_id`) REFERENCES `plm_drive` (`drive_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- 5. Create plm_drive_round table
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

-- 6. Create plm_student_profile table
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

-- 7. Create plm_student_skill table
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

-- 8. Create plm_student_certification table
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

-- 9. Create plm_student_resume table
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


-- =========================================================================
-- SECTION 2: INCREMENTAL DATABASE ALTERATIONS (POST-CREATION PATCHES)
-- =========================================================================

--- shrikant 22/06/2026
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

CREATE TABLE IF NOT EXISTS `plm_company_contact` (
  `contact_id` INT NOT NULL AUTO_INCREMENT,
  `company_id` INT NOT NULL,
  `name` VARCHAR(150) NOT NULL,
  `designation` VARCHAR(100) DEFAULT NULL,
  `email` VARCHAR(150) DEFAULT NULL,
  `phone` VARCHAR(20) DEFAULT NULL,
  `is_primary` TINYINT(1) NOT NULL DEFAULT 0,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `create_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`contact_id`),
  KEY `fk_plm_contact_company` (`company_id`),
  CONSTRAINT `fk_plm_contact_company` FOREIGN KEY (`company_id`) REFERENCES `plm_company` (`company_id`) ON DELETE CASCADE
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
-- SECTION 3: CLEANUP & POPULAR RECRUITERS SEEDING (TPO APPROVAL WORKFLOW)
-- Clear all old drive, slot, application, and company records to avoid stale key issues.
-- Inserts 10 popular multinational/national companies for recruiter self-registration.
-- Status: 0 = Pending (so TPO can manually review and approve on-screen)
-- =========================================================================

SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE plm_post_placement;
TRUNCATE TABLE plm_offer;
TRUNCATE TABLE plm_round_result;
TRUNCATE TABLE plm_shortlist;
TRUNCATE TABLE plm_waitlist;
TRUNCATE TABLE plm_interview_slot;
TRUNCATE TABLE plm_interview_schedule;
TRUNCATE TABLE plm_application;
TRUNCATE TABLE plm_drive_round;
TRUNCATE TABLE plm_drive_eligible_branch;
TRUNCATE TABLE plm_drive;
TRUNCATE TABLE plm_company_contact;
TRUNCATE TABLE plm_company_self_registration;
TRUNCATE TABLE plm_company;
SET FOREIGN_KEY_CHECKS = 1;

INSERT INTO `plm_company_self_registration`
  (`company_name`, `company_type`, `industry`, `website`, `email`, `phone`,
   `address`, `city`, `state`, `country`, `pincode`,
   `contact_person`, `contact_email`, `contact_phone`,
   `description`, `status`, `org_id`, `create_date`)
VALUES
  (
    'Google India Pvt Ltd', 'Multinational', 'Technology / Software', 'https://www.google.com', 'india-recruiting@google.com', '+91 80 6721 8000', 
    'RMZ Infinity, Old Madras Road', 'Bengaluru', 'Karnataka', 'India', '560016', 'Rajesh Kurup', 'rkurup@google.com', '+91 9845012345', 
    'Google is a global technology leader focused on improving the ways people connect with information.', 0, 1, NOW()
  ),
  (
    'Microsoft India', 'Private', 'Technology / Software', 'https://www.microsoft.com/en-in', 'ms-careers@microsoft.com', '+91 40 6695 0000', 
    'Microsoft Campus, Gachibowli', 'Hyderabad', 'Telangana', 'India', '500032', 'Shalini Sen', 'shalini.sen@microsoft.com', '+91 9988776655', 
    'Microsoft enables digital transformation for the era of an intelligent cloud and an intelligent edge.', 0, 1, NOW()
  ),
  (
    'Amazon Development Center India', 'Multinational', 'E-commerce / Tech', 'https://www.amazon.in', 'amazon-hiring@amazon.com', '+91 80 4189 0000', 
    'Brigade Gateway, 26/1 Dr. Rajkumar Road', 'Bengaluru', 'Karnataka', 'India', '560055', 'Amit Saxena', 'asaxena@amazon.com', '+91 9776655443', 
    'Amazon is guided by customer obsession, passion for invention, commitment to operational excellence, and long-term thinking.', 0, 1, NOW()
  ),
  (
    'Accenture India', 'Private', 'IT Consulting / Services', 'https://www.accenture.com', 'accenture.india@accenture.com', '+91 22 2518 8000', 
    'Godrej One, Vikhroli East', 'Mumbai', 'Maharashtra', 'India', '400079', 'Pooja Nair', 'pooja.nair@accenture.com', '+91 9123456789', 
    'Accenture is a leading global professional services company, providing a broad range of services and solutions in strategy, consulting, digital, technology and operations.', 0, 1, NOW()
  ),
  (
    'NVIDIA Graphics Pvt Ltd', 'Multinational', 'Semiconductors / AI', 'https://www.nvidia.com', 'nvidia-recruitment@nvidia.com', '+91 80 6608 8000', 
    'Manyata Embassy Business Park', 'Bengaluru', 'Karnataka', 'India', '560045', 'Vikram Sethi', 'vsethi@nvidia.com', '+91 9898989898', 
    'NVIDIA pioneered GPU computing, a supercharged form of computing that has revolutionized computer graphics, gaming, and artificial intelligence.', 0, 1, NOW()
  ),
  (
    'Intel India', 'Private', 'Semiconductors / Hardware', 'https://www.intel.in', 'intel.india@intel.com', '+91 80 2605 3000', 
    'Outer Ring Road, Devarabeesanahalli', 'Bengaluru', 'Karnataka', 'India', '560103', 'Preeti Desai', 'preeti.desai@intel.com', '+91 9009009009', 
    'Intel designs and builds the essential technologies that serve as the foundation for the world’s revolutionary computing devices.', 0, 1, NOW()
  ),
  (
    'J.P. Morgan Chase & Co.', 'Private', 'Investment Banking / Financial Services', 'https://www.jpmorganchase.com', 'jpmc-recruitment@jpmorgan.com', '+91 22 6125 0000', 
    'Nirlon Knowledge Park, Goregaon East', 'Mumbai', 'Maharashtra', 'India', '400063', 'Rohan Mathur', 'rohan.mathur@jpmorgan.com', '+91 9888877777', 
    'JPMorgan Chase & Co. is a leading global financial services firm and one of the largest banking institutions in the United States.', 0, 1, NOW()
  ),
  (
    'Tata Consultancy Services (TCS)', 'Public', 'IT Services / Consulting', 'https://www.tcs.com', 'tcs.campus@tcs.com', '+91 22 6778 9999', 
    'TCS House, Raveline Street, Fort', 'Mumbai', 'Maharashtra', 'India', '400001', 'Anil Deshmukh', 'anil.deshmukh@tcs.com', '+91 9555544444', 
    'Tata Consultancy Services is an IT services, consulting and business solutions organization that has been partnering with many of the world’s largest businesses.', 0, 1, NOW()
  ),
  (
    'Infosys Limited', 'Public', 'IT Services / Consulting', 'https://www.infosys.com', 'campus.connect@infosys.com', '+91 80 2852 0261', 
    'Electronics City, Hosur Road', 'Bengaluru', 'Karnataka', 'India', '560100', 'Devendra Kumar', 'devendra_k@infosys.com', '+91 9666655555', 
    'Infosys is a global leader in next-generation digital services and consulting, enabling clients in 46 countries to navigate their digital transformation.', 0, 1, NOW()
  ),
  (
    'Larsen & Toubro (L&T)', 'Public', 'Engineering / Construction', 'https://www.larsentoubro.com', 'careers@larsentoubro.com', '+91 22 6752 5656', 
    'L&T House, Ballard Estate', 'Mumbai', 'Maharashtra', 'India', '400001', 'Suresh Pillai', 'suresh.pillai@larsentoubro.com', '+91 9777788888', 
    'Larsen & Toubro is a major technology, engineering, construction, manufacturing and financial services conglomerate, with global operations.', 0, 1, NOW()
  );

-- =========================================================================
-- SECTION 4: INTERVIEW MODULE TABLES
-- Added by: Interview Schedule Feature — 09/07/2026
-- Safe to re-run: uses CREATE TABLE IF NOT EXISTS
-- Tables: plm_interview_schedule, plm_interview_slot,
--         plm_round_result, plm_org_holiday
-- =========================================================================

-- -----------------------------------------------------------------------------
-- 4.1 plm_interview_schedule
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
-- 4.2 plm_interview_slot
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
-- 4.3 plm_round_result
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
-- 4.4 plm_org_holiday
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
-- Quick verification — run after applying Section 4:
-- =========================================================================
-- SHOW TABLES LIKE 'plm_interview%';
-- SHOW TABLES LIKE 'plm_round_result';
-- SHOW TABLES LIKE 'plm_org_holiday';
-- DESC plm_interview_slot;
-- =========================================================================

-- =========================================================================
-- SECTION 5: PLACEMENT DRIVES SEEDING
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
-- SECTION 5: FEATURE ENHANCEMENTS — Interview Scheduling Module
-- Date: 2026-07-11
-- Author: Merged from temp_phase1_migration.sql
-- Features: F2 (interviewer_id, student_id), F4 (notification_sent_at),
--           F5 (notification_expires_at), F6 (profile_status)
-- Safe: All new columns are nullable — existing rows unaffected.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 5.1  plm_interview_slot — New columns
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
-- 5.2  plm_notification_log — New columns
--      F5: expires_at     → copy of slot_time captured at send time (audit trail)
--      F6: profile_status → student's placement_status at moment of notification
-- -----------------------------------------------------------------------------
ALTER TABLE plm_notification_log
    ADD COLUMN expires_at      DATETIME      NULL
        COMMENT 'Notification expiry — copied from slot_time at send time',

    ADD COLUMN profile_status  VARCHAR(30)   NULL
        COMMENT 'plm_student_profile.placement_status at notification time: UNPLACED | APPLIED | IN_PROCESS | PLACED | OPTED_OUT';


-- -----------------------------------------------------------------------------
-- Verification (run manually after applying above):
--   DESC plm_interview_slot;       -- confirm: interviewer_id, student_id,
--                                  --          notification_sent_at, notification_expires_at
--   DESC plm_notification_log;     -- confirm: expires_at, profile_status
-- -----------------------------------------------------------------------------


-- =============================================================================
-- SECTION 6: CONTACT INTERVIEWER FLAG
-- Date: 2026-07-15
-- Adds is_interviewer flag to plm_company_contact so the schedule wizard
-- only shows contacts who are marked as interviewers, not all contacts.
-- Safe: nullable with DEFAULT 0, no existing rows affected.
-- =============================================================================

ALTER TABLE plm_company_contact
    ADD COLUMN is_interviewer TINYINT NOT NULL DEFAULT 0
        COMMENT '1 = this contact can be assigned as an interviewer in schedule wizard'
    AFTER is_primary;


-- =============================================================================
-- SECTION 9: PLM_APPLICATION ENHANCEMENTS
-- Date: 2026-07-16
-- Adds override_reason column to plm_application for override justifications.
-- Safe: nullable, no existing rows affected.
-- =============================================================================

ALTER TABLE plm_application
    ADD COLUMN IF NOT EXISTS override_reason TEXT NULL
        COMMENT 'Reason/justification provided for manual shortlist/reject overrides';

