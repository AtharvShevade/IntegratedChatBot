--------------------------------------------------------
--  File created - Monday-August-04-2025   
--------------------------------------------------------
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_M_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_M_GEN_INFO" 
   (	"DESCRIPTION" VARCHAR2(100), 
	"VALUE" VARCHAR2(100), 
	"CODE" VARCHAR2(20), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_M_SEC9_SENSEC_PARTA
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_M_SEC9_SENSEC_PARTA" 
   (	"DESCRIPTION" VARCHAR2(200), 
	"EXPOSURE_DOM" NUMBER(20,2), 
	"GROSS_AMT_OS_DOM" NUMBER(20,2), 
	"OF_WHICH_IMPAIRED_DOM" NUMBER(20,2), 
	"EXPOSURE_OVE" NUMBER(20,2), 
	"GROSS_AMT_OS_OVE" NUMBER(20,2), 
	"OF_WHICH_IMPAIRED_OVE" NUMBER(20,2), 
	"CODE" NUMBER(20,2), 
	"RDATE" DATE, 
	"TYPE_ID" NUMBER
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_M_SEC9_SENSEC_PARTA_BK
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_M_SEC9_SENSEC_PARTA_BK" 
   (	"DESCRIPTION" VARCHAR2(200), 
	"EXPOSURE_DOM" NUMBER(20,2), 
	"GROSS_AMT_OS_DOM" NUMBER(20,2), 
	"OF_WHICH_IMPAIRED_DOM" NUMBER(20,2), 
	"EXPOSURE_OVE" NUMBER(20,2), 
	"GROSS_AMT_OS_OVE" NUMBER(20,2), 
	"OF_WHICH_IMPAIRED_OVE" NUMBER(20,2), 
	"CODE" NUMBER(20,2), 
	"RDATE" DATE, 
	"TYPE_ID" NUMBER
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_M_SEC9_SENSEC_PARTB
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_M_SEC9_SENSEC_PARTB" 
   (	"DESCRIPTION" VARCHAR2(200), 
	"TOT_EXPO_DOM" NUMBER(20,2), 
	"AMT_OS_FUNDED_DOM" NUMBER(20,2), 
	"RESTRU_STD_DOM" NUMBER(20,2), 
	"IMPAIRED_DOM" NUMBER(20,2), 
	"SLIPPAGE_DOM" NUMBER(20,2), 
	"TOT_EXPO_OVE" NUMBER(20,2), 
	"AMT_OS_FUNDED_OVE" NUMBER(20,2), 
	"RESTRU_STD_OVE" NUMBER(20,2), 
	"IMPAIRED_OVE" NUMBER(20,2), 
	"SLIPPAGE_OVE" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"TYPEID" NUMBER, 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_M_SEC9_SENSEC_PARTB_bckup
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_M_SEC9_SENSEC_PARTB_bckup" 
   (	"DESCRIPTION" VARCHAR2(200), 
	"TOT_EXPO_DOM" NUMBER(20,2), 
	"AMT_OS_FUNDED_DOM" NUMBER(20,2), 
	"RESTRU_STD_DOM" NUMBER(20,2), 
	"IMPAIRED_DOM" NUMBER(20,2), 
	"SLIPPAGE_DOM" NUMBER(20,2), 
	"TOT_EXPO_OVE" NUMBER(20,2), 
	"AMT_OS_FUNDED_OVE" NUMBER(20,2), 
	"RESTRU_STD_OVE" NUMBER(20,2), 
	"IMPAIRED_OVE" NUMBER(20,2), 
	"SLIPPAGE_OVE" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"TYPEID" NUMBER, 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_M_SIGN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_M_SIGN_INFO" 
   (	"DESCRIPTION" VARCHAR2(100), 
	"VALUE" VARCHAR2(100), 
	"CODE" NUMBER, 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_GEN_INFO" 
   (	"DESCRIPTION" VARCHAR2(100), 
	"VALUE" VARCHAR2(100), 
	"CODE" VARCHAR2(20), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC_12_MISC
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC_12_MISC" 
   (	"ITEM" VARCHAR2(100), 
	"VALUE" VARCHAR2(100), 
	"CODE" VARCHAR2(20), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC_12_MISC_T2
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC_12_MISC_T2" 
   (	"CATEGORY" VARCHAR2(200), 
	"IND_MICRO" NUMBER(20,0), 
	"IND_SMALL" NUMBER(20,0), 
	"IND_MEDIUM" NUMBER(20,0), 
	"SER_MICRO" NUMBER(20,0), 
	"SER_SMALL" NUMBER(20,0), 
	"SER_MEDIUM" NUMBER(20,0), 
	"TOT_MICRO" NUMBER(20,0), 
	"TOT_SMALL" NUMBER(20,0), 
	"TOT_MEDIUM" NUMBER(20,0), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC_12_MISC_T3
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC_12_MISC_T3" 
   (	"DESCRIPTION" VARCHAR2(200), 
	"AMT" NUMBER(20,2), 
	"MIN_INT" NUMBER(20,4), 
	"MAX_INT" NUMBER(20,4), 
	"WEGHT_AVG_INT" NUMBER(20,4), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC_12_MISC_T4
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC_12_MISC_T4" 
   (	"DESCRIPTION" VARCHAR2(200), 
	"GROSS_ADV" NUMBER(20,2), 
	"GROSS_NPA" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC1_EXC_GOVT_PAPER
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC1_EXC_GOVT_PAPER" 
   (	"DESCRIPTION" VARCHAR2(100), 
	"VALUE" VARCHAR2(100), 
	"CODE" VARCHAR2(20), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC1_LAST_DATE_PORT
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC1_LAST_DATE_PORT" 
   (	"DESCRIPTION" VARCHAR2(100), 
	"VALUE" VARCHAR2(100), 
	"CODE" VARCHAR2(20), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC1_PART_A_DOM
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC1_PART_A_DOM" 
   (	"PERIOD_DELINQUENCY" VARCHAR2(200), 
	"TERM_LOAN" NUMBER(20,2), 
	"CASH_CR_OVERDRAFT_DEMAND_LOAN" NUMBER(20,2), 
	"BILLS_PURCHASE_DISCOUNT" NUMBER(20,2), 
	"LOAN_ADVANCE_BANK" NUMBER(20,2), 
	"TOTAL_LOAN_ASSETS" NUMBER(20,2), 
	"CODE" NUMBER(20,2), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC1_PART_B_DOM
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC1_PART_B_DOM" 
   (	"PERIOD_DELINQUENCY" VARCHAR2(200), 
	"COMMERCIAL_PAPER" NUMBER(20,2), 
	"NOTE_BONDS_CORPORATE" NUMBER(20,2), 
	"INTER_BANK_ASSETS" NUMBER(20,2), 
	"LEASE_EASE_RECEIVABLE" NUMBER(20,2), 
	"OTHERS" NUMBER(20,2), 
	"TOTAL_OIBA" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC1_PART_C_O
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC1_PART_C_O" 
   (	"PERIOD_DELINQUENCY" VARCHAR2(200), 
	"TERM_LOAN" NUMBER(20,2), 
	"CASH_CR_OVERDRAFT_DEMAND_LOAN" NUMBER(20,2), 
	"BILLS_PURCHASE_DISCOUNT" NUMBER(20,2), 
	"LOAN_ADVANCE_BANK" NUMBER(20,2), 
	"TOTAL_LOAN_ASSETS" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC1_PART_D_O
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC1_PART_D_O" 
   (	"PERIOD_DELINQUENCY" VARCHAR2(200), 
	"COMMERCIAL_PAPER" NUMBER(20,2), 
	"NOTE_BONDS_CORPORATE" NUMBER(20,2), 
	"INTER_BANK_ASSETS" NUMBER(20,2), 
	"OTHERS" NUMBER(20,2), 
	"TOTAL_OIBA" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC10
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC10" 
   (	"DESCRIPTION" VARCHAR2(100), 
	"FUN_EXP" NUMBER(20,2), 
	"NON_FUN_EXP" NUMBER(20,2), 
	"TOTAL" NUMBER(20,2), 
	"AMT_OUT_FUN" NUMBER(20,2), 
	"OF_WHC_IMPAIR" NUMBER(20,2), 
	"LOSS_PRO_HELD" NUMBER(20,2), 
	"INT_MIN" NUMBER(20,2), 
	"INT_MAX" NUMBER(20,2), 
	"INT_WGT_AVG_RATE" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC11
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC11" 
   (	"COUNTRY_BRW_CUNTR_PARTY" VARCHAR2(100), 
	"COUNTRY_RISK" VARCHAR2(100), 
	"SECTOR" VARCHAR2(100), 
	"STD" NUMBER(20,2), 
	"SUB_STD" NUMBER(20,2), 
	"DOUBTFUL" NUMBER(20,2), 
	"LOSS" NUMBER(20,2), 
	"TOTAL" NUMBER(20,2), 
	"OF_SHRT_TR_EXP" NUMBER(20,2), 
	"NET_FUND_TOTAL" NUMBER(20,2), 
	"NET_FUND_OF_SHRT_TR_EXP" NUMBER(20,2), 
	"GR_NONFUND_EXP" NUMBER(20,2), 
	"PROV_HELD_COUNTRY" NUMBER(20,2), 
	"PRO_AS_NET_FUND" NUMBER(20,2), 
	"CODE" VARCHAR2(20), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC2_LAST_DATE_PORT
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC2_LAST_DATE_PORT" 
   (	"DESCRIPTION" VARCHAR2(100), 
	"VALUE" VARCHAR2(100), 
	"CODE" VARCHAR2(20), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC2_PART_A
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC2_PART_A" 
   (	"RISK_CATEGORY" VARCHAR2(200), 
	"OUTSTANDING_AMT_DOM" NUMBER(20,2), 
	"PER_TO_TOTAL_DOM" NUMBER(20,4), 
	"PROVISION_MADE_LOSSES_DOM" NUMBER(20,2), 
	"OUTSTANDING_AMT_O" NUMBER(20,2), 
	"PER_TO_TOTAL_O" NUMBER(20,4), 
	"PROVISION_MADE_LOSSES_O" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC2_PART_A_MEMO
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC2_PART_A_MEMO" 
   (	"MEMORANDUM_ITEM" VARCHAR2(200), 
	"OUTSTANDING_AMT_DOM" NUMBER(20,2), 
	"OUTSTANDING_AMT_O" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC2_PART_A_NPA
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC2_PART_A_NPA" 
   (	"RISK_CATEGORY" VARCHAR2(200), 
	"OUTSTANDING_AMT_DOM" NUMBER(20,2), 
	"OUTSTANDING_AMT_O" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC2_PART_B
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC2_PART_B" 
   (	"MOVEMENT_PROVISION_NPA" VARCHAR2(200), 
	"DOMESTIC" NUMBER(20,2), 
	"OVERSEAS" NUMBER(20,2), 
	"GLOBAL" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC2_PART_C
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC2_PART_C" 
   (	"ITEM" VARCHAR2(200), 
	"STANDARD_DOM" NUMBER(20,2), 
	"SUBSTANDARD_DOM" NUMBER(20,2), 
	"DOUBTFUL_DOM" NUMBER(20,2), 
	"LOSS_DOM" NUMBER(20,2), 
	"TOTAL_DOM" NUMBER(20,2), 
	"STANDARD_O" NUMBER(20,2), 
	"SUBSTANDARD_O" NUMBER(20,2), 
	"DOUBTFUL_O" NUMBER(20,2), 
	"LOSS_O" NUMBER(20,2), 
	"TOTAL_O" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC3_PART_A
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC3_PART_A" 
   (	"CATEGORY" VARCHAR2(200), 
	"DESCRIPTION" VARCHAR2(200), 
	"ACC_RES_DOM" NUMBER(20,2), 
	"ACC_RES_CDR_DOM" NUMBER(20,2), 
	"OUT_ACC_RES_DOM" NUMBER(20,2), 
	"OUT_ACC_RES_CDR_DOM" NUMBER(20,2), 
	"ACC_SLIP_DOM" NUMBER(20,2), 
	"OUT_ACC_SLIP_DOM" NUMBER(20,2), 
	"ACC_RES_OS" NUMBER(20,2), 
	"ACC_RES_CDR_OS" NUMBER(20,2), 
	"OUT_ACC_RES_OS" NUMBER(20,2), 
	"OUT_ACC_RES_CDR_OS" NUMBER(20,2), 
	"ACC_SLIP_OS" NUMBER(20,2), 
	"OUT_ACC_SLIP_OS" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC3_PART_B
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC3_PART_B" 
   (	"MOVEMENT_RESTRUCTURE_STD_LA" VARCHAR2(200), 
	"DOMESTIC" NUMBER(20,2), 
	"OVERSEAS" NUMBER(20,2), 
	"GLOBAL" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE, 
	"TYPE_ID" NUMBER
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC4_PART_A
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC4_PART_A" 
   (	"MOVEMENT_FROM" VARCHAR2(200), 
	"STANDARD_DOM" NUMBER(20,2), 
	"SUBSTANDARD_DOM" NUMBER(20,2), 
	"DOUBTFUL_DOM" NUMBER(20,2), 
	"LOSS_DOM" NUMBER(20,2), 
	"TOTAL_DOM" NUMBER(20,2), 
	"STANDARD_O" NUMBER(20,2), 
	"SUBSTANDARD_O" NUMBER(20,2), 
	"DOUBTFUL_O" NUMBER(20,2), 
	"LOSS_O" NUMBER(20,2), 
	"TOTAL_O" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC4_PART_B
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC4_PART_B" 
   (	"MOVEMENT_FROM" VARCHAR2(200), 
	"SUBSTANDARD_DOM" NUMBER(20,2), 
	"DOUBTFUL_DOM" NUMBER(20,2), 
	"LOSS_DOM" NUMBER(20,2), 
	"TOTAL_DOM" NUMBER(20,2), 
	"SUBSTANDARD_O" NUMBER(20,2), 
	"DOUBTFUL_O" NUMBER(20,2), 
	"LOSS_O" NUMBER(20,2), 
	"TOTAL_O" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC4_PART_C
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC4_PART_C" 
   (	"DESCRIPTION" VARCHAR2(200), 
	"DOMESTIC" NUMBER(20,2), 
	"OVERSEAS" NUMBER(20,2), 
	"GLODAL" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC4_PART_D
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC4_PART_D" 
   (	"DESCRIPTION" VARCHAR2(200), 
	"NO_OF_CASE" NUMBER(20,2), 
	"AMOUNT" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC5_TOP_CR
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC5_TOP_CR" 
   (	"SR_NO" NUMBER, 
	"PAN_DEFAULTER" VARCHAR2(200), 
	"NAME_DEFAULTER" VARCHAR2(200), 
	"DATE_SANCTION" VARCHAR2(200), 
	"RISK_CLASSIFICATION" VARCHAR2(100), 
	"FUND_CR_EXP" NUMBER(20,2), 
	"NONFUND_CR_EXP" NUMBER(20,2), 
	"TOTAL_CR_EXP" NUMBER(20,2), 
	"LOSS_PRO_HELD" NUMBER(20,2), 
	"INTR_ARREARS" NUMBER(20,2), 
	"TOTAL_INV_EXP_IF" NUMBER(20,2), 
	"TOTAL_EXP" NUMBER(20,2), 
	"CODE" VARCHAR2(200), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC5_TOP_CR_TL
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC5_TOP_CR_TL" 
   (	"DESCRIPTION" VARCHAR2(200), 
	"FUND_CR_EXP" NUMBER(20,2), 
	"NONFUND_CR_EXP" NUMBER(20,2), 
	"TOTAL_CR_EXP" NUMBER(20,2), 
	"LOSS_PRO_HELD" NUMBER(20,2), 
	"INTR_ARREARS" NUMBER(20,2), 
	"TOTAL_INV_EXP_IF" NUMBER(20,2), 
	"TOTAL_EXP" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC6_PART_A
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC6_PART_A" 
   (	"CATEGORY_INVESTMENT_DOM_OPR" VARCHAR2(200), 
	"HELD_MATURITY_BV" NUMBER(20,2), 
	"AVAIL_FR_SALE_BV" NUMBER(20,2), 
	"HELD_FR_TRADING_BV" NUMBER(20,2), 
	"TOTAL_BV" NUMBER(20,2), 
	"HELD_MATURITY_MV" NUMBER(20,2), 
	"AVAIL_FR_SALE_MV" NUMBER(20,2), 
	"HELD_FR_TRADING_MV" NUMBER(20,2), 
	"TOTAL_MV" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC6_PART_B
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC6_PART_B" 
   (	"ITEM" VARCHAR2(200), 
	"AMT_CR_QTR" NUMBER(20,2), 
	"AMT_CR_YR" NUMBER(20,2), 
	"TOTAL_CR_QTR" NUMBER(20,2), 
	"TOTAL_CR_YR" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC6_PART_C
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC6_PART_C" 
   (	"CATEGORY" VARCHAR2(200), 
	"ITEM" VARCHAR2(200), 
	"TL_HLD_RATE" NUMBER(20,2), 
	"TL_HLD_UNRATE" NUMBER(20,2), 
	"TL_HLD_BRWR" NUMBER(20,2), 
	"TL_HLD_NONBRWR" NUMBER(20,2), 
	"AATPP_RATE" NUMBER(20,2), 
	"AATPP_UNRATE" NUMBER(20,2), 
	"TOTAL_NPA" NUMBER(20,2), 
	"TOTAL_PRO_HELD" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC6_PART_C_2
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC6_PART_C_2" 
   (	"DESCRIPTION" VARCHAR2(200), 
	"VALUE" VARCHAR2(100), 
	"CODE" VARCHAR2(20), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC6_PART_D
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC6_PART_D" 
   (	"DESCRIPTION" VARCHAR2(100), 
	"DOMESTIC" NUMBER(20,2), 
	"OVERSEAS" NUMBER(20,2), 
	"GLOBAL" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC7_EXP_CR
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC7_EXP_CR" 
   (	"DISBURSH_PRE_RUP_CR" NUMBER(20,2), 
	"DISBURSH_PRE_PCFC" NUMBER(20,2), 
	"DISBURSH_PRE_TOTAL" NUMBER(20,2), 
	"DISBURSH_POST_RUP_CR" NUMBER(20,2), 
	"DISBURSH_POST_EBR" NUMBER(20,2), 
	"DISBURSH_POST_DEFER_PAYMENT" NUMBER(20,2), 
	"DISBURSH_POST_OTR_GOVT_PAYMENT" NUMBER(20,2), 
	"DISBURSH_POST_TOTAL" NUMBER(20,2), 
	"DISBURSH_TOTAL" NUMBER(20,2), 
	"BAL_OUT_PRE_RUP_CR" NUMBER(20,2), 
	"BAL_OUT_PRE_PCFC" NUMBER(20,2), 
	"BAL_OUT_PRE_TOTAL" NUMBER(20,2), 
	"BAL_OUT_POST_RUP_CR" NUMBER(20,2), 
	"BAL_OUT_POST_EBR" NUMBER(20,2), 
	"BAL_OUT_POST_DEFER_PAYMENT" NUMBER(20,2), 
	"BAL_OUT_POST_OTR_GOVT_PAYMENT" NUMBER(20,2), 
	"BAL_OUT_POST_TOTAL" NUMBER(20,2), 
	"BAL_OUT_TOTAL" NUMBER(20,2), 
	"NO_GOLD_CARD_ISSUED" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC8_IND_BRKUP
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC8_IND_BRKUP" 
   (	"INDUSTRY_NAME" VARCHAR2(200), 
	"TL_F_CR_EXP" NUMBER(20,2), 
	"TL_NF_CR_EXP" NUMBER(20,2), 
	"TL_F_AND_NF_CR__EXP" NUMBER(20,2), 
	"TL_INV_EXP" NUMBER(20,2), 
	"TL_EXP" NUMBER(20,2), 
	"FUN_ADV_OUT" NUMBER(20,2), 
	"OF_WCH_SEC_FUN_ADV_OUT" NUMBER(20,2), 
	"NFFUN_ADV_OUT" NUMBER(20,2), 
	"STD_FUN_ADV" NUMBER(20,2), 
	"GROSS_NPA_BEG" NUMBER(20,2), 
	"NEW_ACC_NPA_STD" NUMBER(20,2), 
	"UPGRADATION" NUMBER(20,2), 
	"ACTUAL_RECOVERIES" NUMBER(20,2), 
	"WRITE_OFFS" NUMBER(20,2), 
	"REDUCTION" NUMBER(20,2), 
	"GROSS_NPA_END" NUMBER(20,2), 
	"SMA_0" NUMBER(20,2), 
	"SMA_1" NUMBER(20,2), 
	"SMA_2" NUMBER(20,2), 
	"SUBSTANDARD_ADV" NUMBER(20,2), 
	"DOUBT_ADVANCES" NUMBER(20,2), 
	"LOSS_ADVANCES" NUMBER(20,2), 
	"TOT_LOSS_PRO_HELD" NUMBER(20,2), 
	"CUM_WRITE_OFFS" NUMBER(20,2), 
	"TECH_PRUD_WRITE_OFFS" NUMBER(20,2), 
	"RESTRUCTURED_STAND_ADV" NUMBER(20,2), 
	"TL_TERM_LOANS_SANCT" NUMBER(20,2), 
	"TL_TERM_LOANS_DISBUR" NUMBER(20,2), 
	"TL_BILLS_PURCHASED" NUMBER(20,2), 
	"NET_LOANS_DISBURSED" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE, 
	"TYPEID" NUMBER
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC8_INFRA_BRKUP
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC8_INFRA_BRKUP" 
   (	"INDUSTRY_NAME" VARCHAR2(200), 
	"TL_F_CR_EXP" NUMBER(20,2), 
	"TL_NF_CR_EXP" NUMBER(20,2), 
	"TL_F_AND_NF_CR__EXP" NUMBER(20,2), 
	"TL_INV_EXP" NUMBER(20,2), 
	"TL_EXP" NUMBER(20,2), 
	"FUN_ADV_OUT" NUMBER(20,2), 
	"OF_WCH_SEC_FUN_ADV_OUT" NUMBER(20,2), 
	"NFFUN_ADV_OUT" NUMBER(20,2), 
	"STD_FUN_ADV" NUMBER(20,2), 
	"GROSS_NPA_BEG" NUMBER(20,2), 
	"NEW_ACC_NPA_STD" NUMBER(20,2), 
	"UPGRADATION" NUMBER(20,2), 
	"ACTUAL_RECOVERIES" NUMBER(20,2), 
	"WRITE_OFFS" NUMBER(20,2), 
	"REDUCTION" NUMBER(20,2), 
	"GROSS_NPA_END" NUMBER(20,2), 
	"SMA_0" NUMBER(20,2), 
	"SMA_1" NUMBER(20,2), 
	"SMA_2" NUMBER(20,2), 
	"SUBSTANDARD_ADV" NUMBER(20,2), 
	"DOUBT_ADVANCES" NUMBER(20,2), 
	"LOSS_ADVANCES" NUMBER(20,2), 
	"TOT_LOSS_PRO_HELD" NUMBER(20,2), 
	"CUM_WRITE_OFFS" NUMBER(20,2), 
	"TECH_PRUD_WRITE_OFFS" NUMBER(20,2), 
	"RESTRUCTURED_STAND_ADV" NUMBER(20,2), 
	"TL_TERM_LOANS_SANCT" NUMBER(20,2), 
	"TL_TERM_LOANS_DISBUR" NUMBER(20,2), 
	"TL_BILLS_PURCHASED" NUMBER(20,2), 
	"NET_LOANS_DISBURSED" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE, 
	"TYPEID" NUMBER
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC8_SEC_CREDIT
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC8_SEC_CREDIT" 
   (	"ITEM" VARCHAR2(200), 
	"TL_F_CR_EXP" NUMBER(20,2), 
	"TL_NF_CR_EXP" NUMBER(20,2), 
	"TL_F_AND_NF_CR__EXP" NUMBER(20,2), 
	"TL_INV_EXP" NUMBER(20,2), 
	"TL_EXP" NUMBER(20,2), 
	"FUN_ADV_OUT" NUMBER(20,2), 
	"OF_WCH_SEC_FUN_ADV_OUT" NUMBER(20,2), 
	"NFFUN_ADV_OUT" NUMBER(20,2), 
	"STD_FUN_ADV" NUMBER(20,2), 
	"GROSS_NPA_BEG" NUMBER(20,2), 
	"NEW_ACC_NPA_STD" NUMBER(20,2), 
	"UPGRADATION" NUMBER(20,2), 
	"ACTUAL_RECOVERIES" NUMBER(20,2), 
	"WRITE_OFFS" NUMBER(20,2), 
	"REDUCTION" NUMBER(20,2), 
	"GROSS_NPA_END" NUMBER(20,2), 
	"SMA_0" NUMBER(20,2), 
	"SMA_1" NUMBER(20,2), 
	"SMA_2" NUMBER(20,2), 
	"SUBSTANDARD_ADV" NUMBER(20,2), 
	"DOUBT_ADVANCES" NUMBER(20,2), 
	"LOSS_ADVANCES" NUMBER(20,2), 
	"TOT_LOSS_PRO_HELD" NUMBER(20,2), 
	"CUM_WRITE_OFFS" NUMBER(20,2), 
	"TECH_PRUD_WRITE_OFFS" NUMBER(20,2), 
	"RESTRUCTURED_STAND_ADV" NUMBER(20,2), 
	"TL_TERM_LOANS_SANCT" NUMBER(20,2), 
	"TL_TERM_LOANS_DISBUR" NUMBER(20,2), 
	"TL_BILLS_PURCHASED" NUMBER(20,2), 
	"NET_LOANS_DISBURSED" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE, 
	"TYPEID" NUMBER
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC8_SEC_CREDIT_1
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC8_SEC_CREDIT_1" 
   (	"DESCRIPTION" VARCHAR2(200), 
	"VALUE" VARCHAR2(100), 
	"CODE" VARCHAR2(20), 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC9_SENSEC_PARTA
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC9_SENSEC_PARTA" 
   (	"DESCRIPTION" VARCHAR2(200), 
	"EXPOSURE_DOM" NUMBER(20,2), 
	"GROSS_AMT_OS_DOM" NUMBER(20,2), 
	"OF_WHICH_IMPAIRED_DOM" NUMBER(20,2), 
	"EXPOSURE_OVE" NUMBER(20,2), 
	"GROSS_AMT_OS_OVE" NUMBER(20,2), 
	"OF_WHICH_IMPAIRED_OVE" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE, 
	"TYPE_ID" NUMBER
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC9_SENSEC_PARTA_bkup
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC9_SENSEC_PARTA_bkup" 
   (	"DESCRIPTION" VARCHAR2(200), 
	"EXPOSURE_DOM" NUMBER(20,2), 
	"GROSS_AMT_OS_DOM" NUMBER(20,2), 
	"OF_WHICH_IMPAIRED_DOM" NUMBER(20,2), 
	"EXPOSURE_OVE" NUMBER(20,2), 
	"GROSS_AMT_OS_OVE" NUMBER(20,2), 
	"OF_WHICH_IMPAIRED_OVE" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"RDATE" DATE, 
	"TYPE_ID" NUMBER
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC9_SENSEC_PARTB
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC9_SENSEC_PARTB" 
   (	"DESCRIPTION" VARCHAR2(200), 
	"TOT_EXPO_DOM" NUMBER(20,2), 
	"AMT_OS_FUNDED_DOM" NUMBER(20,2), 
	"RESTRU_STD_DOM" NUMBER(20,2), 
	"IMPAIRED_DOM" NUMBER(20,2), 
	"SLIPPAGE_DOM" NUMBER(20,2), 
	"TOT_EXPO_OVE" NUMBER(20,2), 
	"AMT_OS_FUNDED_OVE" NUMBER(20,2), 
	"RESTRU_STD_OVE" NUMBER(20,2), 
	"IMPAIRED_OVE" NUMBER(20,2), 
	"SLIPPAGE_OVE" NUMBER(20,2), 
	"CODE" NUMBER(20,0), 
	"TYPEID" NUMBER, 
	"RDATE" DATE
   ) ;
--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SIGNATORY
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SIGNATORY" 
   (	"DESCRIPTION" VARCHAR2(100), 
	"VALUE" VARCHAR2(100), 
	"CODE" VARCHAR2(20), 
	"RDATE" DATE
   ) ;
