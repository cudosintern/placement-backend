-- =========================================================================
-- DATABASE SCHEMA DOCUMENTATION - SOUNDARYA'S MODULES
-- Contains CREATE TABLE statements for:
-- 1. plm_company
-- 2. plm_company_contact
-- 3. plm_notification_event_type
-- 4. plm_notification_template
-- 5. plm_notification_log
-- =========================================================================

-- 1. Table: plm_company
CREATE TABLE IF NOT EXISTS `plm_company` (
  `company_id` INT AUTO_INCREMENT PRIMARY KEY,
  `company_name` VARCHAR(200) NOT NULL,
  `company_type` VARCHAR(100) DEFAULT NULL,
  `industry` VARCHAR(100) DEFAULT NULL,
  `website` VARCHAR(255) DEFAULT NULL,
  `email` VARCHAR(150) DEFAULT NULL,
  `phone` VARCHAR(20) DEFAULT NULL,
  `address` TEXT DEFAULT NULL,
  `city` VARCHAR(100) DEFAULT NULL COMMENT 'Stores City ID as string',
  `state` VARCHAR(100) DEFAULT NULL COMMENT 'Stores State ID as string',
  `country` VARCHAR(100) DEFAULT 'India' COMMENT 'Stores Country ID as string',
  `pincode` VARCHAR(10) DEFAULT NULL,
  `contact_person` VARCHAR(150) DEFAULT NULL,
  `contact_designation` VARCHAR(100) DEFAULT NULL COMMENT 'Stores Designation ID as string',
  `contact_phone` VARCHAR(20) DEFAULT NULL,
  `contact_email` VARCHAR(150) DEFAULT NULL,
  `description` TEXT DEFAULT NULL,
  `logo_path` VARCHAR(500) DEFAULT NULL,
  `status` SMALLINT NOT NULL DEFAULT 1 COMMENT '1 = Active, 0 = Inactive',
  `org_id` INT NOT NULL DEFAULT 1,
  `created_by` INT DEFAULT NULL,
  `modified_by` INT DEFAULT NULL,
  `create_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `modify_date` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Table: plm_company_contact
CREATE TABLE IF NOT EXISTS `plm_company_contact` (
  `contact_id` INT AUTO_INCREMENT PRIMARY KEY,
  `company_id` INT NOT NULL,
  `name` VARCHAR(150) NOT NULL,
  `designation` VARCHAR(100) DEFAULT NULL COMMENT 'Stores Designation ID as string',
  `email` VARCHAR(150) DEFAULT NULL,
  `phone` VARCHAR(20) DEFAULT NULL,
  `is_primary` TINYINT DEFAULT 0 COMMENT '1 = Primary, 0 = Regular',
  `is_active` TINYINT DEFAULT 1 COMMENT '1 = Active, 0 = Inactive',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_plm_company_contact_company` FOREIGN KEY (`company_id`)
    REFERENCES `plm_company` (`company_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Table: plm_notification_event_type
CREATE TABLE IF NOT EXISTS `plm_notification_event_type` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `event_code` VARCHAR(100) NOT NULL,
  `event_name` VARCHAR(255) NOT NULL,
  `status` TINYINT DEFAULT 1 COMMENT '1 = Active, 0 = Inactive',
  `org_id` INT DEFAULT 1,
  `created_by` INT DEFAULT NULL,
  `modified_by` INT DEFAULT NULL,
  `create_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `modify_date` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Table: plm_notification_template
CREATE TABLE IF NOT EXISTS `plm_notification_template` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `notification_title` TEXT NOT NULL,
  `notification_message` TEXT NOT NULL,
  `notification_type` VARCHAR(100) NOT NULL COMMENT 'Email, SMS, Push',
  `event_type_id` INT DEFAULT NULL,
  `org_id` INT DEFAULT 1,
  `status` TINYINT DEFAULT 1 COMMENT '1 = Active, 0 = Inactive',
  `created_by` INT DEFAULT NULL,
  `modified_by` INT DEFAULT NULL,
  `create_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `modify_date` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Table: plm_notification_log
CREATE TABLE IF NOT EXISTS `plm_notification_log` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `template_id` INT DEFAULT NULL,
  `recipient` VARCHAR(255) NOT NULL,
  `notification_type` VARCHAR(100) NOT NULL COMMENT 'Email, SMS, Push',
  `subject` TEXT DEFAULT NULL,
  `message` TEXT DEFAULT NULL,
  `status` TINYINT DEFAULT 1 COMMENT '1 = Sent, 0 = Failed',
  `org_id` INT DEFAULT 1,
  `created_by` INT DEFAULT NULL,
  `modified_by` INT DEFAULT NULL,
  `create_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `modify_date` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
