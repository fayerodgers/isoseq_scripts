-- MySQL dump 10.14  Distrib 5.5.52-MariaDB, for Linux (x86_64)
--
-- Host: mysql-wormbase-pipelines    Database: test_isoseq
-- ------------------------------------------------------
-- Server version	5.6.33

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `cds`
--

DROP TABLE IF EXISTS `cds`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `cds` (
  `transcript` varchar(20) NOT NULL DEFAULT '',
  `start` int(11) NOT NULL,
  `end` int(11) NOT NULL,
  `frame` int(1) DEFAULT NULL,
  PRIMARY KEY (`transcript`,`start`),
  CONSTRAINT `fk_id` FOREIGN KEY (`transcript`) REFERENCES `transcripts` (`transcript`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `clusters`
--

DROP TABLE IF EXISTS `clusters`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `clusters` (
  `cluster` int(11) NOT NULL,
  `scaffold` varchar(100) NOT NULL,
  `strand` varchar(10) NOT NULL,
  PRIMARY KEY (`cluster`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `exon_clusters`
--

DROP TABLE IF EXISTS `exon_clusters`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `exon_clusters` (
  `cluster` int(11) NOT NULL,
  `start` int(11) NOT NULL,
  `end` int(11) NOT NULL,
  PRIMARY KEY (`cluster`,`start`),
  CONSTRAINT `fk_cluster_to_exons` FOREIGN KEY (`cluster`) REFERENCES `clusters` (`cluster`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `exons`
--

DROP TABLE IF EXISTS `exons`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `exons` (
  `read_id` int(11) NOT NULL DEFAULT '0',
  `start` int(11) NOT NULL,
  `end` int(11) NOT NULL,
  PRIMARY KEY (`read_id`,`start`),
  CONSTRAINT `fk_read_id` FOREIGN KEY (`read_id`) REFERENCES `isoseq_reads` (`read_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `isoseq_reads`
--

DROP TABLE IF EXISTS `isoseq_reads`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `isoseq_reads` (
  `read_id` int(11) NOT NULL AUTO_INCREMENT,
  `scaffold` varchar(100) NOT NULL,
  `strand` varchar(10) NOT NULL,
  `read_name` varchar(100) NOT NULL,
  `cluster` int(11) DEFAULT NULL,
  `5_prime_cluster` int(11) DEFAULT NULL,
  `library` varchar(100) DEFAULT NULL,
  `intron_validation` int(11) DEFAULT NULL,
  PRIMARY KEY (`read_id`),
  UNIQUE KEY `read_name` (`read_name`),
  UNIQUE KEY `read_name_2` (`read_name`),
  KEY `fk_cluster_to_reads` (`cluster`),
  CONSTRAINT `fk_cluster_to_reads` FOREIGN KEY (`cluster`) REFERENCES `clusters` (`cluster`)
) ENGINE=InnoDB AUTO_INCREMENT=2417181 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `transcripts`
--

DROP TABLE IF EXISTS `transcripts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `transcripts` (
  `transcript` varchar(20) NOT NULL,
  `cluster` int(11) NOT NULL,
  `score` int(11) DEFAULT NULL,
  `type` varchar(20) DEFAULT NULL,
  `gene` int(11) DEFAULT NULL,
  PRIMARY KEY (`transcript`),
  KEY `fk_cluster_to_transcripts` (`cluster`),
  CONSTRAINT `fk_cluster_to_transcripts` FOREIGN KEY (`cluster`) REFERENCES `clusters` (`cluster`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `wb_genes`
--

DROP TABLE IF EXISTS `wb_genes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `wb_genes` (
  `wb_transcript` varchar(100) NOT NULL,
  `isoseq_transcript` varchar(20) NOT NULL,
  `wb_gene` varchar(100) DEFAULT NULL,
  `wb_coverage_exons` decimal(3,2) DEFAULT NULL,
  `iso_coverage_exons` decimal(3,2) DEFAULT NULL,
  `wb_coverage_cds` decimal(3,2) DEFAULT NULL,
  `iso_coverage_cds` decimal(3,2) DEFAULT NULL,
  `relation` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`wb_transcript`,`isoseq_transcript`),
  KEY `fk_transcripts_to_wb_gene` (`isoseq_transcript`),
  CONSTRAINT `fk_transcripts_to_wb_gene` FOREIGN KEY (`isoseq_transcript`) REFERENCES `transcripts` (`transcript`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2019-01-28 16:13:00
