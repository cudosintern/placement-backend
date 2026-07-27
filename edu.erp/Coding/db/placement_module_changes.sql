

-- Dumping structure for table ionerp_placement_2026_new.plm_application
CREATE TABLE IF NOT EXISTS `plm_application` (
  `application_id` int(11) NOT NULL AUTO_INCREMENT,
  `tenant_id` int(11) NOT NULL DEFAULT 1,
  `drive_id` int(11) NOT NULL,
  `profile_id` int(10) unsigned NOT NULL,
  `resume_id` int(11) DEFAULT NULL,
  `applied_at` datetime DEFAULT current_timestamp(),
  `status` varchar(50) NOT NULL DEFAULT 'APPLIED',
  `is_eligible` tinyint(4) NOT NULL DEFAULT 1,
  `override_reason` text DEFAULT NULL,
  PRIMARY KEY (`application_id`),
  KEY `fk_app_drive` (`drive_id`),
  KEY `fk_app_profile` (`profile_id`),
  KEY `fk_app_resume` (`resume_id`),
  CONSTRAINT `fk_app_drive` FOREIGN KEY (`drive_id`) REFERENCES `plm_drive` (`drive_id`),
  CONSTRAINT `fk_app_profile` FOREIGN KEY (`profile_id`) REFERENCES `plm_student_profile` (`profile_id`),
  CONSTRAINT `fk_app_resume` FOREIGN KEY (`resume_id`) REFERENCES `plm_student_resume` (`resume_id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4;

-- Dumping structure for table ionerp_placement_2026_new.plm_company
CREATE TABLE IF NOT EXISTS `plm_company` (
  `company_id` int(11) NOT NULL AUTO_INCREMENT,
  `company_name` varchar(200) NOT NULL,
  `company_type` varchar(100) DEFAULT NULL,
  `industry` varchar(100) DEFAULT NULL,
  `website` varchar(255) DEFAULT NULL,
  `email` varchar(150) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `address` text DEFAULT NULL,
  `city` varchar(100) DEFAULT NULL,
  `state` varchar(100) DEFAULT NULL,
  `country` varchar(100) DEFAULT 'India',
  `pincode` varchar(10) DEFAULT NULL,
  `contact_person` varchar(150) DEFAULT NULL,
  `contact_designation` varchar(100) DEFAULT NULL,
  `contact_phone` varchar(20) DEFAULT NULL,
  `contact_email` varchar(150) DEFAULT NULL,
  `description` text DEFAULT NULL,
  `logo_path` varchar(500) DEFAULT NULL,
  `status` smallint(6) NOT NULL DEFAULT 1,
  `org_id` int(11) NOT NULL DEFAULT 1,
  `created_by` int(11) DEFAULT NULL,
  `modified_by` int(11) DEFAULT NULL,
  `create_date` datetime DEFAULT current_timestamp(),
  `modify_date` datetime DEFAULT NULL ON UPDATE current_timestamp(),
  PRIMARY KEY (`company_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4;

-- Dumping structure for table ionerp_placement_2026_new.plm_company_contact
CREATE TABLE IF NOT EXISTS `plm_company_contact` (
  `contact_id` int(11) NOT NULL AUTO_INCREMENT,
  `company_id` int(11) NOT NULL,
  `name` varchar(150) NOT NULL,
  `designation` varchar(100) DEFAULT NULL,
  `email` varchar(150) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `is_primary` tinyint(4) DEFAULT 0,
  `is_interviewer` tinyint(4) DEFAULT 0,
  `is_active` tinyint(4) DEFAULT 1,
  `created_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`contact_id`),
  KEY `fk_contact_company` (`company_id`),
  CONSTRAINT `fk_contact_company` FOREIGN KEY (`company_id`) REFERENCES `plm_company` (`company_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4;

-- Dumping structure for table ionerp_placement_2026_new.plm_company_self_registration
CREATE TABLE IF NOT EXISTS `plm_company_self_registration` (
  `reg_id` int(11) NOT NULL AUTO_INCREMENT,
  `company_id` int(11) DEFAULT NULL,
  `company_name` varchar(200) NOT NULL,
  `company_type` varchar(100) DEFAULT NULL,
  `industry` varchar(100) DEFAULT NULL,
  `website` varchar(255) DEFAULT NULL,
  `email` varchar(150) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `address` text DEFAULT NULL,
  `city` varchar(100) DEFAULT NULL,
  `state` varchar(100) DEFAULT NULL,
  `country` varchar(100) DEFAULT 'India',
  `pincode` varchar(10) DEFAULT NULL,
  `contact_person` varchar(150) DEFAULT NULL,
  `contact_email` varchar(150) DEFAULT NULL,
  `contact_phone` varchar(20) DEFAULT NULL,
  `description` text DEFAULT NULL,
  `status` smallint(6) NOT NULL DEFAULT 0,
  `reviewed_by` int(11) DEFAULT NULL,
  `review_date` datetime DEFAULT NULL,
  `remarks` varchar(500) DEFAULT NULL,
  `org_id` int(11) NOT NULL DEFAULT 1,
  `submitted_by` int(11) DEFAULT NULL,
  `create_date` datetime DEFAULT current_timestamp(),
  `modify_date` datetime DEFAULT NULL ON UPDATE current_timestamp(),
  PRIMARY KEY (`reg_id`),
  KEY `fk_selfreg_company` (`company_id`),
  CONSTRAINT `fk_selfreg_company` FOREIGN KEY (`company_id`) REFERENCES `plm_company` (`company_id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4;

-- Dumping structure for table ionerp_placement_2026_new.plm_drive
CREATE TABLE IF NOT EXISTS `plm_drive` (
  `drive_id` int(11) NOT NULL AUTO_INCREMENT,
  `company_id` int(11) NOT NULL,
  `drive_name` varchar(200) NOT NULL,
  `job_role` varchar(150) NOT NULL,
  `vacancy_count` smallint(6) DEFAULT NULL,
  `drive_type` varchar(50) NOT NULL DEFAULT 'On-Campus',
  `work_type` varchar(50) NOT NULL DEFAULT 'Onsite',
  `location` varchar(200) DEFAULT NULL,
  `ctc_min` decimal(10,2) DEFAULT NULL,
  `ctc_max` decimal(10,2) DEFAULT NULL,
  `job_description` text DEFAULT NULL,
  `min_cgpa` decimal(4,2) NOT NULL DEFAULT 0.00,
  `max_backlogs` smallint(6) NOT NULL DEFAULT 0,
  `application_start` date DEFAULT NULL,
  `application_deadline` date DEFAULT NULL,
  `drive_date` date DEFAULT NULL,
  `tier` smallint(6) NOT NULL DEFAULT 1,
  `status` smallint(6) NOT NULL DEFAULT 0,
  `eligible_student_count` int(11) NOT NULL DEFAULT 0,
  `applied_count` int(11) NOT NULL DEFAULT 0,
  `shortlisted_count` int(11) NOT NULL DEFAULT 0,
  `org_id` int(11) NOT NULL DEFAULT 1,
  `created_by` int(11) DEFAULT NULL,
  `modified_by` int(11) DEFAULT NULL,
  `create_date` datetime DEFAULT current_timestamp(),
  `modify_date` datetime DEFAULT NULL ON UPDATE current_timestamp(),
  PRIMARY KEY (`drive_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4;

-- Dumping structure for table ionerp_placement_2026_new.plm_drive_eligible_branch
CREATE TABLE IF NOT EXISTS `plm_drive_eligible_branch` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `drive_id` int(11) NOT NULL,
  `dept_id` int(11) NOT NULL,
  `batch_year` smallint(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=451 DEFAULT CHARSET=utf8mb4;

-- Dumping structure for table ionerp_placement_2026_new.plm_drive_round
CREATE TABLE IF NOT EXISTS `plm_drive_round` (
  `round_id` int(11) NOT NULL AUTO_INCREMENT,
  `drive_id` int(11) NOT NULL,
  `round_number` smallint(6) NOT NULL,
  `round_name` varchar(150) NOT NULL,
  `round_type` varchar(50) NOT NULL,
  `is_eliminatory` smallint(6) NOT NULL DEFAULT 1,
  `round_date` date DEFAULT NULL,
  `duration_minutes` smallint(6) DEFAULT NULL,
  `description` text DEFAULT NULL,
  PRIMARY KEY (`round_id`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4;

-- Dumping structure for table ionerp_placement_2026_new.plm_interview_schedule
CREATE TABLE IF NOT EXISTS `plm_interview_schedule` (
  `schedule_id` int(11) NOT NULL AUTO_INCREMENT,
  `tenant_id` int(11) DEFAULT 1,
  `drive_id` int(11) NOT NULL,
  `round_id` int(11) NOT NULL,
  `org_id` int(11) NOT NULL DEFAULT 1,
  `venue_type` varchar(50) DEFAULT NULL,
  `venue_details` text DEFAULT NULL,
  `meeting_link` varchar(500) DEFAULT NULL,
  `scheduled_date` date DEFAULT NULL,
  `end_date` date DEFAULT NULL,
  `start_time` varchar(10) DEFAULT NULL,
  `end_time` varchar(10) DEFAULT NULL,
  `scheduling_mode` varchar(30) DEFAULT NULL,
  `batch_size` smallint(6) DEFAULT NULL,
  `total_students` int(11) DEFAULT NULL,
  `total_slots` int(11) DEFAULT NULL,
  `days_required` int(11) DEFAULT NULL,
  `interviewer_names` varchar(500) DEFAULT NULL,
  `interviewer_email` varchar(500) DEFAULT NULL,
  `is_active` tinyint(4) DEFAULT 1,
  `status` varchar(20) DEFAULT NULL,
  `created_by` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT NULL ON UPDATE current_timestamp(),
  `day_start_time` varchar(10) DEFAULT '09:00',
  `day_end_time` varchar(10) DEFAULT '17:00',
  `notification_sent_count` int(11) DEFAULT 0,
  `last_notification_sent_at` datetime DEFAULT NULL,
  PRIMARY KEY (`schedule_id`),
  KEY `fk_schedule_drive` (`drive_id`),
  KEY `fk_schedule_round` (`round_id`),
  CONSTRAINT `fk_schedule_drive` FOREIGN KEY (`drive_id`) REFERENCES `plm_drive` (`drive_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_schedule_round` FOREIGN KEY (`round_id`) REFERENCES `plm_drive_round` (`round_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4;

-- Dumping structure for table ionerp_placement_2026_new.plm_interview_slot
CREATE TABLE IF NOT EXISTS `plm_interview_slot` (
  `slot_id` int(11) NOT NULL AUTO_INCREMENT,
  `schedule_id` int(11) NOT NULL,
  `application_id` int(11) NOT NULL,
  `slot_time` datetime DEFAULT NULL,
  `batch_number` smallint(6) DEFAULT NULL,
  `seq_number` smallint(6) DEFAULT NULL,
  `interviewer_name` varchar(150) DEFAULT NULL,
  `interviewer_email` varchar(150) DEFAULT NULL,
  `status` varchar(50) DEFAULT 'SCHEDULED',
  `notification_sent_at` datetime DEFAULT NULL,
  `notification_status` varchar(20) DEFAULT NULL,
  `interviewer_id` int(11) DEFAULT NULL,
  `student_id` int(11) DEFAULT NULL,
  `notification_expires_at` datetime DEFAULT NULL,
  `contact_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`slot_id`),
  KEY `fk_slot_schedule` (`schedule_id`),
  KEY `fk_slot_app` (`application_id`),
  KEY `fk_slot_contact` (`contact_id`),
  CONSTRAINT `fk_slot_app` FOREIGN KEY (`application_id`) REFERENCES `plm_application` (`application_id`),
  CONSTRAINT `fk_slot_contact` FOREIGN KEY (`contact_id`) REFERENCES `plm_company_contact` (`contact_id`) ON DELETE SET NULL,
  CONSTRAINT `fk_slot_schedule` FOREIGN KEY (`schedule_id`) REFERENCES `plm_interview_schedule` (`schedule_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4;

-- Dumping structure for table ionerp_placement_2026_new.plm_notification_event_type
CREATE TABLE IF NOT EXISTS `plm_notification_event_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `event_code` varchar(100) NOT NULL,
  `event_name` varchar(255) NOT NULL,
  `status` tinyint(4) DEFAULT 1,
  `org_id` int(11) DEFAULT NULL,
  `created_by` int(11) DEFAULT NULL,
  `modified_by` int(11) DEFAULT NULL,
  `create_date` datetime DEFAULT current_timestamp(),
  `modify_date` datetime DEFAULT NULL ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Dumping data for table ionerp_placement_2026_new.plm_notification_event_type: ~0 rows (approximately)

-- Dumping structure for table ionerp_placement_2026_new.plm_notification_log
CREATE TABLE IF NOT EXISTS `plm_notification_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `template_id` int(11) DEFAULT NULL,
  `recipient` varchar(255) NOT NULL,
  `notification_type` varchar(100) NOT NULL,
  `subject` text DEFAULT NULL,
  `message` text DEFAULT NULL,
  `status` tinyint(4) DEFAULT 1,
  `org_id` int(11) DEFAULT NULL,
  `created_by` int(11) DEFAULT NULL,
  `modified_by` int(11) DEFAULT NULL,
  `create_date` datetime DEFAULT current_timestamp(),
  `modify_date` datetime DEFAULT NULL ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Dumping data for table ionerp_placement_2026_new.plm_notification_log: ~0 rows (approximately)

-- Dumping structure for table ionerp_placement_2026_new.plm_notification_template
CREATE TABLE IF NOT EXISTS `plm_notification_template` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `notification_title` text NOT NULL,
  `notification_message` text NOT NULL,
  `notification_type` varchar(100) NOT NULL,
  `event_type_id` int(11) DEFAULT NULL,
  `org_id` int(11) DEFAULT NULL,
  `status` tinyint(4) DEFAULT 1,
  `created_by` int(11) DEFAULT NULL,
  `modified_by` int(11) DEFAULT NULL,
  `create_date` datetime DEFAULT current_timestamp(),
  `modify_date` datetime DEFAULT NULL ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Dumping data for table ionerp_placement_2026_new.plm_notification_template: ~0 rows (approximately)

-- Dumping structure for table ionerp_placement_2026_new.plm_offer
CREATE TABLE IF NOT EXISTS `plm_offer` (
  `offer_id` int(11) NOT NULL AUTO_INCREMENT,
  `tenant_id` int(11) NOT NULL,
  `application_id` int(11) NOT NULL,
  `drive_id` int(11) NOT NULL,
  `profile_id` int(10) unsigned NOT NULL,
  `ctc` decimal(12,2) DEFAULT NULL,
  `role` varchar(200) DEFAULT NULL,
  `location` varchar(200) DEFAULT NULL,
  `joining_date` date DEFAULT NULL,
  `offer_letter_path` varchar(500) DEFAULT NULL,
  `is_ppo` tinyint(4) DEFAULT 0,
  `status` varchar(50) NOT NULL DEFAULT 'ISSUED',
  `issued_at` datetime DEFAULT current_timestamp(),
  `accepted_at` datetime DEFAULT NULL,
  `declined_at` datetime DEFAULT NULL,
  `revoked_at` datetime DEFAULT NULL,
  `decline_reason` text DEFAULT NULL,
  `revoke_reason` text DEFAULT NULL,
  `generated_from_template` tinyint(4) DEFAULT 0,
  `template_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`offer_id`),
  UNIQUE KEY `application_id` (`application_id`),
  KEY `fk_offer_drive` (`drive_id`),
  KEY `fk_offer_profile` (`profile_id`),
  CONSTRAINT `fk_offer_app` FOREIGN KEY (`application_id`) REFERENCES `plm_application` (`application_id`),
  CONSTRAINT `fk_offer_drive` FOREIGN KEY (`drive_id`) REFERENCES `plm_drive` (`drive_id`),
  CONSTRAINT `fk_offer_profile` FOREIGN KEY (`profile_id`) REFERENCES `plm_student_profile` (`profile_id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4;

-- Dumping structure for table ionerp_placement_2026_new.plm_offer_cap_policy
CREATE TABLE IF NOT EXISTS `plm_offer_cap_policy` (
  `policy_id` int(11) NOT NULL AUTO_INCREMENT,
  `tenant_id` int(11) NOT NULL,
  `batch_year` year(4) NOT NULL,
  `max_offers_per_student` tinyint(4) DEFAULT 1,
  `allow_multiple` tinyint(4) DEFAULT 0,
  `effective_from` date NOT NULL,
  `effective_to` date DEFAULT NULL,
  `created_by` int(11) NOT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`policy_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Dumping data for table ionerp_placement_2026_new.plm_offer_cap_policy: ~0 rows (approximately)

-- Dumping structure for table ionerp_placement_2026_new.plm_org_holiday
CREATE TABLE IF NOT EXISTS `plm_org_holiday` (
  `holiday_id` int(11) NOT NULL AUTO_INCREMENT,
  `holiday_date` date NOT NULL,
  `holiday_name` varchar(150) DEFAULT NULL,
  `holiday_type` varchar(10) DEFAULT NULL,
  `org_id` int(11) NOT NULL,
  `is_active` tinyint(4) DEFAULT 1,
  `created_by` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`holiday_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Dumping data for table ionerp_placement_2026_new.plm_org_holiday: ~0 rows (approximately)

-- Dumping structure for table ionerp_placement_2026_new.plm_post_placement
CREATE TABLE IF NOT EXISTS `plm_post_placement` (
  `pp_id` int(11) NOT NULL AUTO_INCREMENT,
  `offer_id` int(11) NOT NULL,
  `joining_confirmation_date` date DEFAULT NULL,
  `actual_joining_date` date DEFAULT NULL,
  `status` varchar(50) NOT NULL DEFAULT 'CONFIRMED',
  `no_show_reason` text DEFAULT NULL,
  `deferral_date` date DEFAULT NULL,
  `alumni_linked` tinyint(4) DEFAULT 0,
  `alumni_record_id` int(11) DEFAULT NULL,
  `recorded_by` int(11) NOT NULL,
  `recorded_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`pp_id`),
  UNIQUE KEY `offer_id` (`offer_id`),
  CONSTRAINT `fk_pp_offer` FOREIGN KEY (`offer_id`) REFERENCES `plm_offer` (`offer_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4;

-- Dumping structure for table ionerp_placement_2026_new.plm_round_result
CREATE TABLE IF NOT EXISTS `plm_round_result` (
  `result_id` int(11) NOT NULL AUTO_INCREMENT,
  `application_id` int(11) NOT NULL,
  `round_id` int(11) NOT NULL,
  `result` varchar(50) NOT NULL,
  `feedback_notes` text DEFAULT NULL,
  `recorded_by` int(11) NOT NULL,
  `recorded_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`result_id`),
  KEY `fk_result_app` (`application_id`),
  KEY `fk_result_round` (`round_id`),
  CONSTRAINT `fk_result_app` FOREIGN KEY (`application_id`) REFERENCES `plm_application` (`application_id`),
  CONSTRAINT `fk_result_round` FOREIGN KEY (`round_id`) REFERENCES `plm_drive_round` (`round_id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4;

-- Dumping structure for table ionerp_placement_2026_new.plm_shortlist
CREATE TABLE IF NOT EXISTS `plm_shortlist` (
  `shortlist_id` int(11) NOT NULL AUTO_INCREMENT,
  `application_id` int(11) NOT NULL,
  `shortlist_type` varchar(50) NOT NULL DEFAULT 'SYSTEM',
  `shortlisted_by` int(11) DEFAULT NULL,
  `justification` text DEFAULT NULL,
  `override_approved_by` int(11) DEFAULT NULL,
  `override_approved_at` datetime DEFAULT NULL,
  `shortlisted_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`shortlist_id`),
  UNIQUE KEY `application_id` (`application_id`),
  CONSTRAINT `fk_shortlist_app` FOREIGN KEY (`application_id`) REFERENCES `plm_application` (`application_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Dumping data for table ionerp_placement_2026_new.plm_shortlist: ~0 rows (approximately)

-- Dumping structure for table ionerp_placement_2026_new.plm_student_certification
CREATE TABLE IF NOT EXISTS `plm_student_certification` (
  `certification_id` int(11) NOT NULL AUTO_INCREMENT,
  `profile_id` int(10) unsigned NOT NULL,
  `student_id` int(11) NOT NULL,
  `certification_name` varchar(255) NOT NULL,
  `issuing_organization` varchar(255) DEFAULT NULL,
  `issue_date` date DEFAULT NULL,
  `expiry_date` date DEFAULT NULL,
  `credential_id` varchar(150) DEFAULT NULL,
  `credential_url` varchar(500) DEFAULT NULL,
  `org_id` int(11) NOT NULL,
  `status` tinyint(4) DEFAULT 1,
  `created_by` int(11) DEFAULT NULL,
  `modified_by` int(11) DEFAULT NULL,
  `created_date` datetime DEFAULT current_timestamp(),
  `modified_date` datetime DEFAULT NULL ON UPDATE current_timestamp(),
  PRIMARY KEY (`certification_id`),
  KEY `fk_cert_profile` (`profile_id`),
  CONSTRAINT `fk_cert_profile` FOREIGN KEY (`profile_id`) REFERENCES `plm_student_profile` (`profile_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4;

-- Dumping structure for table ionerp_placement_2026_new.plm_student_profile
CREATE TABLE IF NOT EXISTS `plm_student_profile` (
  `profile_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `student_id` int(10) unsigned NOT NULL,
  `linkedin_url` varchar(255) DEFAULT NULL,
  `github_url` varchar(255) DEFAULT NULL,
  `portfolio_url` varchar(255) DEFAULT NULL,
  `resume_path` varchar(500) DEFAULT NULL,
  `current_cgpa` decimal(4,2) DEFAULT NULL,
  `backlogs` int(11) DEFAULT 0,
  `is_placement_eligible` tinyint(4) DEFAULT 1,
  `career_objective` text DEFAULT NULL,
  `preferred_locations` varchar(255) DEFAULT NULL,
  `org_id` int(11) NOT NULL,
  `status` tinyint(4) DEFAULT 1,
  `created_by` int(11) DEFAULT NULL,
  `modified_by` int(11) DEFAULT NULL,
  `created_date` datetime DEFAULT current_timestamp(),
  `modified_date` datetime DEFAULT NULL ON UPDATE current_timestamp(),
  `placement_status` varchar(50) NOT NULL DEFAULT 'UNPLACED',
  `is_locked` tinyint(4) NOT NULL DEFAULT 0,
  `active_offer_count` tinyint(4) DEFAULT 0,
  PRIMARY KEY (`profile_id`),
  UNIQUE KEY `student_id` (`student_id`),
  CONSTRAINT `fk_profile_student` FOREIGN KEY (`student_id`) REFERENCES `iems_students` (`student_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4;

-- Dumping structure for table ionerp_placement_2026_new.plm_student_resume
CREATE TABLE IF NOT EXISTS `plm_student_resume` (
  `resume_id` int(11) NOT NULL AUTO_INCREMENT,
  `profile_id` int(10) unsigned NOT NULL,
  `student_id` int(11) NOT NULL,
  `file_name` varchar(255) NOT NULL,
  `stored_name` varchar(500) NOT NULL,
  `file_path` varchar(1000) NOT NULL,
  `file_size_kb` int(11) DEFAULT NULL,
  `is_active` tinyint(4) DEFAULT 1,
  `org_id` int(11) NOT NULL,
  `status` tinyint(4) DEFAULT 1,
  `created_by` int(11) DEFAULT NULL,
  `modified_by` int(11) DEFAULT NULL,
  `created_date` datetime DEFAULT current_timestamp(),
  `modified_date` datetime DEFAULT NULL ON UPDATE current_timestamp(),
  PRIMARY KEY (`resume_id`),
  KEY `fk_resume_profile` (`profile_id`),
  CONSTRAINT `fk_resume_profile` FOREIGN KEY (`profile_id`) REFERENCES `plm_student_profile` (`profile_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4;

-- Dumping structure for table ionerp_placement_2026_new.plm_student_skill
CREATE TABLE IF NOT EXISTS `plm_student_skill` (
  `skill_id` int(11) NOT NULL AUTO_INCREMENT,
  `profile_id` int(10) unsigned NOT NULL,
  `student_id` int(11) NOT NULL,
  `skill_name` varchar(150) NOT NULL,
  `proficiency_level` varchar(50) DEFAULT NULL,
  `org_id` int(11) NOT NULL,
  `status` tinyint(4) DEFAULT 1,
  `created_by` int(11) DEFAULT NULL,
  `modified_by` int(11) DEFAULT NULL,
  `created_date` datetime DEFAULT current_timestamp(),
  `modified_date` datetime DEFAULT NULL ON UPDATE current_timestamp(),
  PRIMARY KEY (`skill_id`),
  KEY `fk_skill_profile` (`profile_id`),
  CONSTRAINT `fk_skill_profile` FOREIGN KEY (`profile_id`) REFERENCES `plm_student_profile` (`profile_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4;

-- Dumping structure for table ionerp_placement_2026_new.plm_waitlist
CREATE TABLE IF NOT EXISTS `plm_waitlist` (
  `waitlist_id` int(11) NOT NULL AUTO_INCREMENT,
  `application_id` int(11) NOT NULL,
  `drive_id` int(11) NOT NULL,
  `position` smallint(6) NOT NULL,
  `promoted_at` datetime DEFAULT NULL,
  `promoted_by` int(11) DEFAULT NULL,
  PRIMARY KEY (`waitlist_id`),
  UNIQUE KEY `application_id` (`application_id`),
  KEY `fk_waitlist_drive` (`drive_id`),
  CONSTRAINT `fk_waitlist_app` FOREIGN KEY (`application_id`) REFERENCES `plm_application` (`application_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_waitlist_drive` FOREIGN KEY (`drive_id`) REFERENCES `plm_drive` (`drive_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
