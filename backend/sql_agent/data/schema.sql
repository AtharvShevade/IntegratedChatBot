--------------------------------------------------------
--  File created - Friday-May-15-2026   
--------------------------------------------------------

--------------------------------------------------------
--  DDL for Table ASSETS_MASTERRLC_CIMS
--------------------------------------------------------

  CREATE TABLE "ASSETS_MASTERRLC_CIMS" ("ASSETS_CLASSFICATION" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table ASSETS_MASTER_CIMS
--------------------------------------------------------

  CREATE TABLE "ASSETS_MASTER_CIMS" ("ASSETS_CLASSFICATION" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table BANKING_ARRANGEMENT_MASTERRLC_CIMS
--------------------------------------------------------

  CREATE TABLE "BANKING_ARRANGEMENT_MASTERRLC_CIMS" ("BANKING_ARRANGEMENT" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table BANKING_ARRANGEMENT_MASTER_CIMS
--------------------------------------------------------

  CREATE TABLE "BANKING_ARRANGEMENT_MASTER_CIMS" ("BANKING_ARRANGEMENT" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table BORROWER_CLASSIFICATION_MASTER_CIMS
--------------------------------------------------------

  CREATE TABLE "BORROWER_CLASSIFICATION_MASTER_CIMS" ("BORROWER_CLASS" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table BRANCH_MASTER_CIMS
--------------------------------------------------------

  CREATE TABLE "BRANCH_MASTER_CIMS" ("BRANCH" VARCHAR2(200), "BANKWORKINGCODE" VARCHAR2(200), "BRANCHCODE" VARCHAR2(200), "COUNTRYNAME" VARCHAR2(200), "COUNTRYCODE" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table BRANCH_MASTER_DOMESTIC_CIMS
--------------------------------------------------------

  CREATE TABLE "BRANCH_MASTER_DOMESTIC_CIMS" ("BRANCH" VARCHAR2(200), "BANKWORKINGCODE" VARCHAR2(200), "BRANCHCODE" VARCHAR2(200), "LOADDATE" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CA_FINAL_17
--------------------------------------------------------

  CREATE TABLE "CA_FINAL_17" ("PAN" VARCHAR2(500), "MONTH1" VARCHAR2(500), "MONTH2" VARCHAR2(500), "MONTH3" VARCHAR2(500), "MONTH4" VARCHAR2(500));

--------------------------------------------------------
--  DDL for Table CA_FINAL_18
--------------------------------------------------------

  CREATE TABLE "CA_FINAL_18" ("PAN" VARCHAR2(250), "MONTH1" VARCHAR2(500), "MNTH1V" VARCHAR2(500), "MONTH2" VARCHAR2(500), "MNTH2V" VARCHAR2(500), "MONTH3" VARCHAR2(500), "MNTH3V" VARCHAR2(500), "MONTH4" VARCHAR2(500), "MNTH4V" VARCHAR2(500));

--------------------------------------------------------
--  DDL for Table CA_FINAL_19
--------------------------------------------------------

  CREATE TABLE "CA_FINAL_19" ("PAN" VARCHAR2(255), "MONTH1" VARCHAR2(255), "MONTH2" VARCHAR2(255), "MONTH3" VARCHAR2(255), "MONTH4" VARCHAR2(255));

--------------------------------------------------------
--  DDL for Table CA_FINAL_20
--------------------------------------------------------

  CREATE TABLE "CA_FINAL_20" ("PAN" VARCHAR2(250), "MONTH1" VARCHAR2(500), "MONTH2" VARCHAR2(500), "MONTH3" VARCHAR2(500), "MONTH4" VARCHAR2(500));

--------------------------------------------------------
--  DDL for Table CA_FINAL_21
--------------------------------------------------------

  CREATE TABLE "CA_FINAL_21" ("PAN" VARCHAR2(250), "FIRSTMONTHRANK" NUMBER, "SECONDMONTHRANK" NUMBER, "THIRDMONTHRANK" NUMBER, "FOURTHMONTHRANK" NUMBER);

--------------------------------------------------------
--  DDL for Table CA_FINAL_22
--------------------------------------------------------

  CREATE TABLE "CA_FINAL_22" ("PAN" VARCHAR2(100), "TE_AS_PRCNT_OF_CAPITAL_FUNDS" NUMBER(20,4), "TOTAL_EXPOSURE" NUMBER(20,2), "SECOND_MONTH_TE_AS_PRCNT_OF_CAPITAL_FUNDS" NUMBER(20,4), "SECONDMONTHTOTAL_EXPOSURE" NUMBER(20,2), "THIRD_MONTH_TE_AS_PRCNT_OF_CAPITAL_FUNDS" NUMBER(20,4), "THIRDMONTHTOTAL_EXPOSURE" NUMBER(20,2), "FOURTH_MONTH_TE_AS_PRCNT_OF_CAPITAL_FUNDS" NUMBER(20,4), "FOURTHMONTHTOTAL_EXPOSURE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_FINAL_23
--------------------------------------------------------

  CREATE TABLE "CA_FINAL_23" ("MONTH1" VARCHAR2(500), "AST1" VARCHAR2(500), "TE1" VARCHAR2(500), "MONTH2" VARCHAR2(500), "AST2" VARCHAR2(500), "TE2" VARCHAR2(500), "MONTH3" VARCHAR2(500), "AST3" VARCHAR2(500), "TE3" VARCHAR2(500), "MONTH4" VARCHAR2(500), "AST4" VARCHAR2(500), "TE4" VARCHAR2(500));

--------------------------------------------------------
--  DDL for Table CA_FINAL_24
--------------------------------------------------------

  CREATE TABLE "CA_FINAL_24" ("MONTH1" VARCHAR2(500), "AST1" VARCHAR2(500), "TE1" VARCHAR2(500), "MONTH2" VARCHAR2(500), "AST2" VARCHAR2(500), "TE2" VARCHAR2(500), "MONTH3" VARCHAR2(500), "AST3" VARCHAR2(500), "TE3" VARCHAR2(500), "MONTH4" VARCHAR2(500), "AST4" VARCHAR2(500), "TE4" VARCHAR2(500));

--------------------------------------------------------
--  DDL for Table CA_FINAL_25
--------------------------------------------------------

  CREATE TABLE "CA_FINAL_25" ("PAN" VARCHAR2(100), "MONTH1" VARCHAR2(20), "MONTH2" VARCHAR2(20), "MONTH3" VARCHAR2(20), "MONTH4" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CA_FINAL_29
--------------------------------------------------------

  CREATE TABLE "CA_FINAL_29" ("PAN" VARCHAR2(250), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "MONTH1" NUMBER(20,2), "MONTH2" NUMBER, "MONTH3" NUMBER, "MONTH4" NUMBER);

--------------------------------------------------------
--  DDL for Table CA_FINAL_33
--------------------------------------------------------

  CREATE TABLE "CA_FINAL_33" ("PAN" VARCHAR2(250), "MONTH1" VARCHAR2(250), "MONTH2" VARCHAR2(250), "MONTH3" VARCHAR2(250), "MONTH4" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_FINAL_35
--------------------------------------------------------

  CREATE TABLE "CA_FINAL_35" ("PAN" VARCHAR2(250), "MONTH1" VARCHAR2(1000), "MONTH2" VARCHAR2(1000), "MONTH3" VARCHAR2(1000), "MONTH4" VARCHAR2(1000));

--------------------------------------------------------
--  DDL for Table CA_FINAL_36
--------------------------------------------------------

  CREATE TABLE "CA_FINAL_36" ("PAN" VARCHAR2(250), "MONTH1" VARCHAR2(1000), "MONTH2" VARCHAR2(1000), "MONTH3" VARCHAR2(1000), "MONTH4" VARCHAR2(1000));

--------------------------------------------------------
--  DDL for Table CA_MASTERLIST_23
--------------------------------------------------------

  CREATE TABLE "CA_MASTERLIST_23" ("PAN" VARCHAR2(250), "CNT" NUMBER);

--------------------------------------------------------
--  DDL for Table CA_MASTERLIST_24
--------------------------------------------------------

  CREATE TABLE "CA_MASTERLIST_24" ("PAN" VARCHAR2(250), "CNT" NUMBER);

--------------------------------------------------------
--  DDL for Table CA_MONTH1_17
--------------------------------------------------------

  CREATE TABLE "CA_MONTH1_17" ("PAN" VARCHAR2(500), "ASSETS_CLASSIFICATION" VARCHAR2(500), "REPORTING_DATE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CA_MONTH1_18
--------------------------------------------------------

  CREATE TABLE "CA_MONTH1_18" ("PAN" VARCHAR2(250), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "SPECIAL_MENTION_ACCOUNTS" VARCHAR2(1000), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH1_19
--------------------------------------------------------

  CREATE TABLE "CA_MONTH1_19" ("PAN" VARCHAR2(255), "INDUSTRYCODE" VARCHAR2(255), "REPORTING_DATE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CA_MONTH1_20
--------------------------------------------------------

  CREATE TABLE "CA_MONTH1_20" ("PAN" VARCHAR2(250), "BORROWER_GROUP_CODE" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH1_21
--------------------------------------------------------

  CREATE TABLE "CA_MONTH1_21" ("PAN" VARCHAR2(250), "TOTAL_EXPOSURE" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250), "RANK" NUMBER);

--------------------------------------------------------
--  DDL for Table CA_MONTH1_22
--------------------------------------------------------

  CREATE TABLE "CA_MONTH1_22" ("PAN" VARCHAR2(100), "TE_AS_PRCNT_OF_CAPITAL_FUNDS" NUMBER(20,4), "TOTAL_EXPOSURE" NUMBER(20,2));

--------------------------------------------------------
--  DDL for Table CA_MONTH1_23
--------------------------------------------------------

  CREATE TABLE "CA_MONTH1_23" ("PAN" VARCHAR2(250), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "TOTAL_EXPOSURE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH1_24
--------------------------------------------------------

  CREATE TABLE "CA_MONTH1_24" ("PAN" VARCHAR2(250), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "TOTAL_EXPOSURE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH1_25
--------------------------------------------------------

  CREATE TABLE "CA_MONTH1_25" ("PAN" VARCHAR2(100), "DATEOFNPA" VARCHAR2(20), "REPORTING_DATE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CA_MONTH1_29
--------------------------------------------------------

  CREATE TABLE "CA_MONTH1_29" ("PAN" VARCHAR2(250), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "TOTAL_EXPOSURE" NUMBER(20,2), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH1_33
--------------------------------------------------------

  CREATE TABLE "CA_MONTH1_33" ("PAN" VARCHAR2(250), "CUSTOMER_NAME" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH1_35
--------------------------------------------------------

  CREATE TABLE "CA_MONTH1_35" ("PAN" VARCHAR2(250), "BANKING_ARRANGEMENT" VARCHAR2(1000), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH1_36
--------------------------------------------------------

  CREATE TABLE "CA_MONTH1_36" ("PAN" VARCHAR2(250), "EXTERNAL_RATING" VARCHAR2(1000), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH2_17
--------------------------------------------------------

  CREATE TABLE "CA_MONTH2_17" ("PAN" VARCHAR2(50), "ASSETS_CLASSIFICATION" VARCHAR2(500), "REPORTING_DATE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CA_MONTH2_18
--------------------------------------------------------

  CREATE TABLE "CA_MONTH2_18" ("PAN" VARCHAR2(250), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "SPECIAL_MENTION_ACCOUNTS" VARCHAR2(1000), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH2_19
--------------------------------------------------------

  CREATE TABLE "CA_MONTH2_19" ("PAN" VARCHAR2(255), "INDUSTRYCODE" VARCHAR2(255), "REPORTING_DATE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CA_MONTH2_20
--------------------------------------------------------

  CREATE TABLE "CA_MONTH2_20" ("PAN" VARCHAR2(100), "BORROWER_GROUP_CODE" VARCHAR2(100), "REPORTINGDATE" VARCHAR2(50));

--------------------------------------------------------
--  DDL for Table CA_MONTH2_21
--------------------------------------------------------

  CREATE TABLE "CA_MONTH2_21" ("PAN" VARCHAR2(250), "TOTAL_EXPOSURE" VARCHAR2(250), "RANK" NUMBER);

--------------------------------------------------------
--  DDL for Table CA_MONTH2_22
--------------------------------------------------------

  CREATE TABLE "CA_MONTH2_22" ("PAN" VARCHAR2(100), "TE_AS_PRCNT_OF_CAPITAL_FUNDS" NUMBER(20,4), "TOTAL_EXPOSURE" NUMBER(20,2));

--------------------------------------------------------
--  DDL for Table CA_MONTH2_23
--------------------------------------------------------

  CREATE TABLE "CA_MONTH2_23" ("PAN" VARCHAR2(250), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "TOTAL_EXPOSURE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH2_24
--------------------------------------------------------

  CREATE TABLE "CA_MONTH2_24" ("PAN" VARCHAR2(250), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "TOTAL_EXPOSURE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH2_25
--------------------------------------------------------

  CREATE TABLE "CA_MONTH2_25" ("PAN" VARCHAR2(100), "DATEOFNPA" VARCHAR2(20), "REPORTINGDATE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CA_MONTH2_29
--------------------------------------------------------

  CREATE TABLE "CA_MONTH2_29" ("PAN" VARCHAR2(250), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "TOTAL_EXPOSURE" NUMBER(20,2), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH2_33
--------------------------------------------------------

  CREATE TABLE "CA_MONTH2_33" ("PAN" VARCHAR2(250), "CUSTOMER_NAME" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH2_35
--------------------------------------------------------

  CREATE TABLE "CA_MONTH2_35" ("PAN" VARCHAR2(250), "BANKING_ARRANGEMENT" VARCHAR2(1000), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH2_36
--------------------------------------------------------

  CREATE TABLE "CA_MONTH2_36" ("PAN" VARCHAR2(250), "EXTERNAL_RATING" VARCHAR2(1000), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH3_17
--------------------------------------------------------

  CREATE TABLE "CA_MONTH3_17" ("PAN" VARCHAR2(50), "ASSETS_CLASSIFICATION" VARCHAR2(500), "REPORTING_DATE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CA_MONTH3_18
--------------------------------------------------------

  CREATE TABLE "CA_MONTH3_18" ("PAN" VARCHAR2(250), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "SPECIAL_MENTION_ACCOUNTS" VARCHAR2(1000), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH3_19
--------------------------------------------------------

  CREATE TABLE "CA_MONTH3_19" ("PAN" VARCHAR2(255), "INDUSTRYCODE" VARCHAR2(255), "REPORTING_DATE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CA_MONTH3_20
--------------------------------------------------------

  CREATE TABLE "CA_MONTH3_20" ("PAN" VARCHAR2(100), "BORROWER_GROUP_CODE" VARCHAR2(100), "REPORTINGDATE" VARCHAR2(50));

--------------------------------------------------------
--  DDL for Table CA_MONTH3_21
--------------------------------------------------------

  CREATE TABLE "CA_MONTH3_21" ("PAN" VARCHAR2(100), "TOTALEXPOSURE" NUMBER, "RANK" NUMBER);

--------------------------------------------------------
--  DDL for Table CA_MONTH3_22
--------------------------------------------------------

  CREATE TABLE "CA_MONTH3_22" ("PAN" VARCHAR2(100), "TE_AS_PRCNT_OF_CAPITAL_FUNDS" NUMBER(20,4), "TOTALEXPOSURE" NUMBER(20,2));

--------------------------------------------------------
--  DDL for Table CA_MONTH3_23
--------------------------------------------------------

  CREATE TABLE "CA_MONTH3_23" ("PAN" VARCHAR2(250), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "TOTAL_EXPOSURE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH3_24
--------------------------------------------------------

  CREATE TABLE "CA_MONTH3_24" ("PAN" VARCHAR2(250), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "TOTAL_EXPOSURE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH3_25
--------------------------------------------------------

  CREATE TABLE "CA_MONTH3_25" ("PAN" VARCHAR2(100), "DATEOFNPA" VARCHAR2(20), "REPORTINGDATE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CA_MONTH3_29
--------------------------------------------------------

  CREATE TABLE "CA_MONTH3_29" ("PAN" VARCHAR2(250), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "TOTAL_EXPOSURE" NUMBER(20,2), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH3_33
--------------------------------------------------------

  CREATE TABLE "CA_MONTH3_33" ("PAN" VARCHAR2(250), "CUSTOMER_NAME" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH3_35
--------------------------------------------------------

  CREATE TABLE "CA_MONTH3_35" ("PAN" VARCHAR2(250), "BANKING_ARRANGEMENT" VARCHAR2(1000), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH3_36
--------------------------------------------------------

  CREATE TABLE "CA_MONTH3_36" ("PAN" VARCHAR2(250), "EXTERNAL_RATING" VARCHAR2(1000), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH4_17
--------------------------------------------------------

  CREATE TABLE "CA_MONTH4_17" ("PAN" VARCHAR2(50), "ASSETS_CLASSIFICATION" VARCHAR2(500), "REPORTING_DATE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CA_MONTH4_18
--------------------------------------------------------

  CREATE TABLE "CA_MONTH4_18" ("PAN" VARCHAR2(250), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "SPECIAL_MENTION_ACCOUNTS" VARCHAR2(1000), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH4_19
--------------------------------------------------------

  CREATE TABLE "CA_MONTH4_19" ("PAN" VARCHAR2(255), "INDUSTRYCODE" VARCHAR2(255), "REPORTING_DATE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CA_MONTH4_20
--------------------------------------------------------

  CREATE TABLE "CA_MONTH4_20" ("PAN" VARCHAR2(100), "BORROWER_GROUP_CODE" VARCHAR2(100), "REPORTINGDATE" VARCHAR2(50));

--------------------------------------------------------
--  DDL for Table CA_MONTH4_21
--------------------------------------------------------

  CREATE TABLE "CA_MONTH4_21" ("PAN" VARCHAR2(100), "TOTALEXPOSURE" NUMBER, "RANK" NUMBER);

--------------------------------------------------------
--  DDL for Table CA_MONTH4_22
--------------------------------------------------------

  CREATE TABLE "CA_MONTH4_22" ("PAN" VARCHAR2(250), "TE_AS_PRCNT_OF_CAPITAL_FUNDS" NUMBER(20,4), "TOTAL_EXPOSURE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH4_23
--------------------------------------------------------

  CREATE TABLE "CA_MONTH4_23" ("PAN" VARCHAR2(250), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "TOTAL_EXPOSURE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH4_24
--------------------------------------------------------

  CREATE TABLE "CA_MONTH4_24" ("PAN" VARCHAR2(250), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "TOTAL_EXPOSURE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH4_25
--------------------------------------------------------

  CREATE TABLE "CA_MONTH4_25" ("PAN" VARCHAR2(100), "DATEOFNPA" VARCHAR2(20), "REPORTINGDATE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CA_MONTH4_29
--------------------------------------------------------

  CREATE TABLE "CA_MONTH4_29" ("PAN" VARCHAR2(250), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "TOTAL_EXPOSURE" NUMBER(20,2), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH4_33
--------------------------------------------------------

  CREATE TABLE "CA_MONTH4_33" ("PAN" VARCHAR2(250), "CUSTOMER_NAME" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH4_35
--------------------------------------------------------

  CREATE TABLE "CA_MONTH4_35" ("PAN" VARCHAR2(250), "BANKING_ARRANGEMENT" VARCHAR2(1000), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CA_MONTH4_36
--------------------------------------------------------

  CREATE TABLE "CA_MONTH4_36" ("PAN" VARCHAR2(250), "EXTERNAL_RATING" VARCHAR2(1000), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_ANX_1_A
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_ANX_1_A" ("AC_BNK_IND" VARCHAR2(100), "DB_NO" NUMBER(20,2), "DB_AMT" NUMBER(20,2), "CR_NO" NUMBER(20,2), "CR_AMT" NUMBER(20,2), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_ANX_1_B
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_ANX_1_B" ("AC_BNK_IND" VARCHAR2(100), "DB_NO" NUMBER(20,2), "DB_AMT" NUMBER(20,2), "CR_NO" NUMBER(20,2), "CR_AMT" NUMBER(20,2), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_ANX_1_BAL
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_ANX_1_BAL" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_ANX_1_LOSS_PRO_IBA
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_ANX_1_LOSS_PRO_IBA" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_ANX_1_LOSS_PRO_IND
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_ANX_1_LOSS_PRO_IND" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_ANX_1_LOSS_PRO_OVR
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_ANX_1_LOSS_PRO_OVR" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_ANX_2
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_ANX_2" ("AC_BNK_IND" VARCHAR2(100), "DB_NO" NUMBER(20,2), "DB_AMT" NUMBER(20,2), "CR_NO" NUMBER(20,2), "CR_AMT" NUMBER(20,2), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_SEC2_D1
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_SEC2_D1" ("DERIVATIVE" VARCHAR2(100), "NAT_PRIN_TL" NUMBER(20,2), "NAT_PRI_OUT_TL_DR" NUMBER(20,2), "CR_CUR_CR_EXP" NUMBER(20,2), "CR_PTN_EXP" NUMBER(20,2), "NGT_MTM_VAL" NUMBER(20,2), "PVBP_SANC_LMT" NUMBER(20,2), "PVBP_ACTUAL" NUMBER(20,2), "VAR_SANC_LMT" NUMBER(20,2), "VAT_ACTUAL" NUMBER(20,2), "REMARK" VARCHAR2(100), "CODE" VARCHAR2(200), "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_SEC2_D2
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_SEC2_D2" ("DERIVATIVE" VARCHAR2(100), "NAT_PRIN_TL" NUMBER(20,2), "NAT_PRI_OUT_TL_DR" NUMBER(20,2), "CR_CUR_CR_EXP" NUMBER(20,2), "CR_PTN_EXP" NUMBER(20,2), "NGT_MTM_VAL" NUMBER(20,2), "PVBP_SANC_LMT" NUMBER(20,2), "PVBP_ACTUAL" NUMBER(20,2), "VAR_SANC_LMT" NUMBER(20,2), "VAT_ACTUAL" NUMBER(20,2), "REMARK" VARCHAR2(100), "CODE" VARCHAR2(200), "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_SEC2_E1
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_SEC2_E1" ("ITEM" VARCHAR2(100), "TRADE_BNK_PAYS" NUMBER(20,2), "TRADE_BNK_REC" NUMBER(20,2), "HEDG_BNK_PAYS" NUMBER(20,2), "HEDG_BNK_REC" NUMBER(20,2), "TL_NAT_PRI" NUMBER(20,2), "GROSS_REC_TB" NUMBER(20,2), "GROSS_REC_BB" NUMBER(20,2), "GROSS_REC_TOTAL" NUMBER(20,2), "GROSS_PAID_REC_TB" NUMBER(20,2), "GROSS_PAID_REC_BB" NUMBER(20,2), "GROSS_PAID_REC_TOTAL" NUMBER(20,2), "HIGHER" NUMBER(20,2), "NET_PVBP" NUMBER(20,2), "REMARK" VARCHAR2(100), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_SEC2_E2
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_SEC2_E2" ("ITEM" VARCHAR2(100), "TRADE_BNK_PAYS" NUMBER(20,2), "TRADE_BNK_REC" NUMBER(20,2), "HEDG_BNK_PAYS" NUMBER(20,2), "HEDG_BNK_REC" NUMBER(20,2), "TL_NAT_PRI" NUMBER(20,2), "GROSS_REC_TB" NUMBER(20,2), "GROSS_REC_BB" NUMBER(20,2), "GROSS_REC_TOTAL" NUMBER(20,2), "GROSS_PAID_REC_TB" NUMBER(20,2), "GROSS_PAID_REC_BB" NUMBER(20,2), "GROSS_PAID_REC_TOTAL" NUMBER(20,2), "HIGHER" NUMBER(20,2), "NET_PVBP" NUMBER(20,2), "REMARK" VARCHAR2(100), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_SEC2_F1
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_SEC2_F1" ("ITEM" VARCHAR2(200), "NAT_PROT_BUY" NUMBER(20,2), "NAT_PROT_SELL" NUMBER(20,2), "AT_END_NAT_PROT_BUY" NUMBER(20,2), "AT_END_NAT_PROT_SELL" NUMBER(20,2), "CODE" VARCHAR2(200), "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_SEC2_F2
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_SEC2_F2" ("ITEM" VARCHAR2(200), "NAT_PROT_BUY" NUMBER(20,2), "NAT_PROT_SELL" NUMBER(20,2), "AT_END_NAT_PROT_BUY" NUMBER(20,2), "AT_END_NAT_PROT_SELL" NUMBER(20,2), "CODE" VARCHAR2(200), "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_SEC2_G1_BK_FI
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_SEC2_G1_BK_FI" ("SR_NO" NUMBER, "NAME_BK_FI" VARCHAR2(100), "NAT_AMT" NUMBER(20,2), "CUR_CR_EXP" NUMBER(20,2), "POT_FUT_EXP" NUMBER(20,2), "90_DY_PAST_AMT" NUMBER(20,2), "ACTUAL_CR_LOSS" NUMBER(20,2), "RESTRUCT_CONT" NUMBER(20,2), "TRANSACTIONID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_SEC2_G1_BK_FI_DCB
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_SEC2_G1_BK_FI_DCB" ("SR_NO" NUMBER, "NAME_BK_FI" VARCHAR2(100), "NAT_AMT" NUMBER(20,2), "CUR_CR_EXP" NUMBER(20,2), "POT_FUT_EXP" NUMBER(20,2), "NINETY_DY_PAST_AMT" NUMBER(20,2), "ACTUAL_CR_LOSS" NUMBER(20,2), "RESTRUCT_CONT" NUMBER(20,2), "TRANSACTIONID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_SEC2_G1_CORP_OTR
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_SEC2_G1_CORP_OTR" ("SR_NO" NUMBER, "NAME_BK_FI" VARCHAR2(100), "NAT_AMT" NUMBER(20,2), "CUR_CR_EXP" NUMBER(20,2), "POT_FUT_EXP" NUMBER(20,2), "90_DY_PAST_AMT" NUMBER(20,2), "ACTUAL_CR_LOSS" NUMBER(20,2), "RESTRUCT_CONT" NUMBER(20,2), "TRANSACTIONID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_SEC2_G1_COR_OTR_DCB
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_SEC2_G1_COR_OTR_DCB" ("SR_NO" NUMBER, "NAME_BK_FI" VARCHAR2(100), "NAT_AMT" NUMBER(20,2), "CUR_CR_EXP" NUMBER(20,2), "POT_FUT_EXP" NUMBER(20,2), "NINETY_DY_PAST_AMT" NUMBER(20,2), "ACTUAL_CR_LOSS" NUMBER(20,2), "RESTRUCT_CONT" NUMBER(20,2), "TRANSACTIONID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_SEC2_G2_BK_FI
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_SEC2_G2_BK_FI" ("SR_NO" NUMBER, "NAME_BK_FI" VARCHAR2(100), "NAT_AMT" NUMBER(20,2), "CUR_CR_EXP" NUMBER(20,2), "POT_FUT_EXP" NUMBER(20,2), "90_DY_PAST_AMT" NUMBER(20,2), "ACTUAL_CR_LOSS" NUMBER(20,2), "RESTRUCT_CONT" NUMBER(20,2), "TRANSACTIONID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_SEC2_G2_BK_FI_DCB
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_SEC2_G2_BK_FI_DCB" ("SR_NO" NUMBER, "NAME_BK_FI" VARCHAR2(100), "NAT_AMT" NUMBER(20,2), "CUR_CR_EXP" NUMBER(20,2), "POT_FUT_EXP" NUMBER(20,2), "NINETY_DY_PAST_AMT" NUMBER(20,2), "ACTUAL_CR_LOSS" NUMBER(20,2), "RESTRUCT_CONT" NUMBER(20,2), "TRANSACTIONID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_SEC2_G2_CORP_OTR
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_SEC2_G2_CORP_OTR" ("SR_NO" NUMBER, "NAME_BK_FI" VARCHAR2(100), "NAT_AMT" NUMBER(20,2), "CUR_CR_EXP" NUMBER(20,2), "POT_FUT_EXP" NUMBER(20,2), "90_DY_PAST_AMT" NUMBER(20,2), "ACTUAL_CR_LOSS" NUMBER(20,2), "RESTRUCT_CONT" NUMBER(20,2), "TRANSACTIONID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_SEC2_G2_COR_OTR_DCB
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_SEC2_G2_COR_OTR_DCB" ("SR_NO" NUMBER, "NAME_BK_FI" VARCHAR2(100), "NAT_AMT" NUMBER(20,2), "CUR_CR_EXP" NUMBER(20,2), "POT_FUT_EXP" NUMBER(20,2), "NINETY_DY_PAST_AMT" NUMBER(20,2), "ACTUAL_CR_LOSS" NUMBER(20,2), "RESTRUCT_CONT" NUMBER(20,2), "TRANSACTIONID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_SEC_1A
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_SEC_1A" ("ASSETS" VARCHAR2(200), "DOM_AMT_TOT" NUMBER, "DOM_AMT_FRX" NUMBER, "OVR_AMT_TOT" NUMBER, "OVR_AMT_FRX" NUMBER, "GBL_AMT_TOT" NUMBER, "GBL_AMT_FRX" NUMBER, "CODE" NUMBER, "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_SEC_1B
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_SEC_1B" ("ASSETS" VARCHAR2(200), "DOM_AMT_TOT" NUMBER, "DOM_AMT_FRX" NUMBER, "OVR_AMT_TOT" NUMBER, "OVR_AMT_FRX" NUMBER, "GBL_AMT_TOT" NUMBER, "GBL_AMT_FRX" NUMBER, "CODE" NUMBER, "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_SEC_1C
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_SEC_1C" ("ASSETS" VARCHAR2(200), "DOM_AMT_TOT" NUMBER, "DOM_AMT_FRX" NUMBER, "OVR_AMT_TOT" NUMBER, "OVR_AMT_FRX" NUMBER, "GBL_AMT_TOT" NUMBER, "GBL_AMT_FRX" NUMBER, "CODE" NUMBER, "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_SEC_2A
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_SEC_2A" ("CONTRACTS" VARCHAR2(200), "BOK_VAL_DOM" NUMBER, "CR_EQV_DOM" NUMBER, "BOK_VAL_OS" NUMBER, "CR_EQV_OS" NUMBER, "BOK_VAL_GOBL" NUMBER, "CR_EQV_GOBL" NUMBER, "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_SEC_2B
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_SEC_2B" ("CONTRACTS" VARCHAR2(200), "PRIN_TURN_OVR" NUMBER, "PRIN_OUT" NUMBER, "TRADE_TURN_OVR" NUMBER, "TRADE_OUT" NUMBER, "BANK_TURN_OVR" NUMBER, "BANK_OUT" NUMBER, "CR_PRIN_AMT" NUMBER, "CR_TRADE_OUT" NUMBER, "CR_BANK_OUT" NUMBER, "CODE" NUMBER, "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_SEC_2C
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_SEC_2C" ("CONTRACTS" VARCHAR2(200), "PRIN_TURN_OVR" NUMBER, "PRIN_OUT" NUMBER, "TRADE_TURN_OVR" NUMBER, "TRADE_OUT" NUMBER, "BANK_TURN_OVR" NUMBER, "BANK_OUT" NUMBER, "CR_PRIN_AMT" NUMBER, "CR_TRADE_OUT" NUMBER, "CR_BANK_OUT" NUMBER, "CODE" NUMBER, "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_M_SIGNATORY
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_M_SIGNATORY" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_ANX_1_A
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_ANX_1_A" ("AC_BNK_IND" VARCHAR2(100), "DB_NO" NUMBER(20,2), "DB_AMT" NUMBER(20,2), "CR_NO" NUMBER(20,2), "CR_AMT" NUMBER(20,2), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_ANX_1_B
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_ANX_1_B" ("AC_BNK_IND" VARCHAR2(100), "DB_NO" NUMBER(20,2), "DB_AMT" NUMBER(20,2), "CR_NO" NUMBER(20,2), "CR_AMT" NUMBER(20,2), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_ANX_1_BAL
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_ANX_1_BAL" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_ANX_1_LOSS_PRO_IBA
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_ANX_1_LOSS_PRO_IBA" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_ANX_1_LOSS_PRO_IND
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_ANX_1_LOSS_PRO_IND" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_ANX_1_LOSS_PRO_OVR
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_ANX_1_LOSS_PRO_OVR" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_ANX_2
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_ANX_2" ("AC_BNK_IND" VARCHAR2(100), "DB_NO" NUMBER(20,2), "DB_AMT" NUMBER(20,2), "CR_NO" NUMBER(20,2), "CR_AMT" NUMBER(20,2), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_SEC2_D1
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_SEC2_D1" ("DERIVATIVE" VARCHAR2(100), "NAT_PRIN_TL" NUMBER(20,2), "NAT_PRI_OUT_TL_DR" NUMBER(20,2), "CR_CUR_CR_EXP" NUMBER(20,2), "CR_PTN_EXP" NUMBER(20,2), "NGT_MTM_VAL" NUMBER(20,2), "PVBP_SANC_LMT" NUMBER(20,2), "PVBP_ACTUAL" NUMBER(20,2), "VAR_SANC_LMT" NUMBER(20,2), "VAT_ACTUAL" NUMBER(20,2), "REMARK" VARCHAR2(100), "CODE" VARCHAR2(200), "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_SEC2_D2
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_SEC2_D2" ("DERIVATIVE" VARCHAR2(100), "NAT_PRIN_TL" NUMBER(20,2), "NAT_PRI_OUT_TL_DR" NUMBER(20,2), "CR_CUR_CR_EXP" NUMBER(20,2), "CR_PTN_EXP" NUMBER(20,2), "NGT_MTM_VAL" NUMBER(20,2), "PVBP_SANC_LMT" NUMBER(20,2), "PVBP_ACTUAL" NUMBER(20,2), "VAR_SANC_LMT" NUMBER(20,2), "VAT_ACTUAL" NUMBER(20,2), "REMARK" VARCHAR2(100), "CODE" VARCHAR2(200), "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_SEC2_E1
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_SEC2_E1" ("ITEM" VARCHAR2(100), "TRADE_BNK_PAYS" NUMBER(20,2), "TRADE_BNK_REC" NUMBER(20,2), "HEDG_BNK_PAYS" NUMBER(20,2), "HEDG_BNK_REC" NUMBER(20,2), "TL_NAT_PRI" NUMBER(20,2), "GROSS_REC_TB" NUMBER(20,2), "GROSS_REC_BB" NUMBER(20,2), "GROSS_REC_TOTAL" NUMBER(20,2), "GROSS_PAID_REC_TB" NUMBER(20,2), "GROSS_PAID_REC_BB" NUMBER(20,2), "GROSS_PAID_REC_TOTAL" NUMBER(20,2), "HIGHER" NUMBER(20,2), "NET_PVBP" NUMBER(20,2), "REMARK" VARCHAR2(100), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_SEC2_E2
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_SEC2_E2" ("ITEM" VARCHAR2(100), "TRADE_BNK_PAYS" NUMBER(20,2), "TRADE_BNK_REC" NUMBER(20,2), "HEDG_BNK_PAYS" NUMBER(20,2), "HEDG_BNK_REC" NUMBER(20,2), "TL_NAT_PRI" NUMBER(20,2), "GROSS_REC_TB" NUMBER(20,2), "GROSS_REC_BB" NUMBER(20,2), "GROSS_REC_TOTAL" NUMBER(20,2), "GROSS_PAID_REC_TB" NUMBER(20,2), "GROSS_PAID_REC_BB" NUMBER(20,2), "GROSS_PAID_REC_TOTAL" NUMBER(20,2), "HIGHER" NUMBER(20,2), "NET_PVBP" NUMBER(20,2), "REMARK" VARCHAR2(100), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_SEC2_F1
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_SEC2_F1" ("ITEM" VARCHAR2(200), "NAT_PROT_BUY" NUMBER(20,2), "NAT_PROT_SELL" NUMBER(20,2), "AT_END_NAT_PROT_BUY" NUMBER(20,2), "AT_END_NAT_PROT_SELL" NUMBER(20,2), "CODE" VARCHAR2(200), "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_SEC2_F2
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_SEC2_F2" ("ITEM" VARCHAR2(200), "NAT_PROT_BUY" NUMBER(20,2), "NAT_PROT_SELL" NUMBER(20,2), "AT_END_NAT_PROT_BUY" NUMBER(20,2), "AT_END_NAT_PROT_SELL" NUMBER(20,2), "CODE" VARCHAR2(200), "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_SEC2_G1_BK_FI
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_SEC2_G1_BK_FI" ("SR_NO" NUMBER, "NAME_BK_FI" VARCHAR2(100), "NAT_AMT" NUMBER(20,2), "CUR_CR_EXP" NUMBER(20,2), "POT_FUT_EXP" NUMBER(20,2), "90_DY_PAST_AMT" NUMBER(20,2), "ACTUAL_CR_LOSS" NUMBER(20,2), "RESTRUCT_CONT" NUMBER(20,2), "TRANSACTIONID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_SEC2_G1_CORP_OTR
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_SEC2_G1_CORP_OTR" ("SR_NO" NUMBER, "NAME_BK_FI" VARCHAR2(100), "NAT_AMT" NUMBER(20,2), "CUR_CR_EXP" NUMBER(20,2), "POT_FUT_EXP" NUMBER(20,2), "90_DY_PAST_AMT" NUMBER(20,2), "ACTUAL_CR_LOSS" NUMBER(20,2), "RESTRUCT_CONT" NUMBER(20,2), "TRANSACTIONID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_SEC2_G2_BK_FI
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_SEC2_G2_BK_FI" ("SR_NO" NUMBER, "NAME_BK_FI" VARCHAR2(100), "NAT_AMT" NUMBER(20,2), "CUR_CR_EXP" NUMBER(20,2), "POT_FUT_EXP" NUMBER(20,2), "90_DY_PAST_AMT" NUMBER(20,2), "ACTUAL_CR_LOSS" NUMBER(20,2), "RESTRUCT_CONT" NUMBER(20,2), "TRANSACTIONID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_SEC2_G2_CORP_OTR
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_SEC2_G2_CORP_OTR" ("SR_NO" NUMBER, "NAME_BK_FI" VARCHAR2(100), "NAT_AMT" NUMBER(20,2), "CUR_CR_EXP" NUMBER(20,2), "POT_FUT_EXP" NUMBER(20,2), "90_DY_PAST_AMT" NUMBER(20,2), "ACTUAL_CR_LOSS" NUMBER(20,2), "RESTRUCT_CONT" NUMBER(20,2), "TRANSACTIONID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_SEC_1A
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_SEC_1A" ("ASSETS" VARCHAR2(200), "DOM_AMT_TOT" NUMBER, "DOM_AMT_FRX" NUMBER, "OVR_AMT_TOT" NUMBER, "OVR_AMT_FRX" NUMBER, "GBL_AMT_TOT" NUMBER, "GBL_AMT_FRX" NUMBER, "CODE" NUMBER, "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_SEC_1B
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_SEC_1B" ("ASSETS" VARCHAR2(200), "DOM_AMT_TOT" NUMBER, "DOM_AMT_FRX" NUMBER, "OVR_AMT_TOT" NUMBER, "OVR_AMT_FRX" NUMBER, "GBL_AMT_TOT" NUMBER, "GBL_AMT_FRX" NUMBER, "CODE" NUMBER, "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_SEC_1C
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_SEC_1C" ("ASSETS" VARCHAR2(200), "DOM_AMT_TOT" NUMBER, "DOM_AMT_FRX" NUMBER, "OVR_AMT_TOT" NUMBER, "OVR_AMT_FRX" NUMBER, "GBL_AMT_TOT" NUMBER, "GBL_AMT_FRX" NUMBER, "CODE" NUMBER, "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_SEC_2A
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_SEC_2A" ("CONTRACTS" VARCHAR2(200), "BOK_VAL_DOM" NUMBER, "CR_EQV_DOM" NUMBER, "BOK_VAL_OS" NUMBER, "CR_EQV_OS" NUMBER, "BOK_VAL_GOBL" NUMBER, "CR_EQV_GOBL" NUMBER, "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_SEC_2B
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_SEC_2B" ("CONTRACTS" VARCHAR2(200), "PRIN_TURN_OVR" NUMBER, "PRIN_OUT" NUMBER, "TRADE_TURN_OVR" NUMBER, "TRADE_OUT" NUMBER, "BANK_TURN_OVR" NUMBER, "BANK_OUT" NUMBER, "CR_PRIN_AMT" NUMBER, "CR_TRADE_OUT" NUMBER, "CR_BANK_OUT" NUMBER, "CODE" NUMBER, "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_SEC_2C
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_SEC_2C" ("CONTRACTS" VARCHAR2(200), "PRIN_TURN_OVR" NUMBER, "PRIN_OUT" NUMBER, "TRADE_TURN_OVR" NUMBER, "TRADE_OUT" NUMBER, "BANK_TURN_OVR" NUMBER, "BANK_OUT" NUMBER, "CR_PRIN_AMT" NUMBER, "CR_TRADE_OUT" NUMBER, "CR_BANK_OUT" NUMBER, "CODE" NUMBER, "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_ALE_Q_SIGNATORY
--------------------------------------------------------

  CREATE TABLE "CIMS_ALE_Q_SIGNATORY" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALO_Q_ANNEX1
--------------------------------------------------------

  CREATE TABLE "CIMS_ALO_Q_ANNEX1" ("SR_NO" NUMBER, "COUNTRY_CODE" VARCHAR2(3), "BRANCH_CODE" VARCHAR2(20), "DETAILS_OFF_BS_EXPO" VARCHAR2(300), "VALUE" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table CIMS_ALO_Q_ANNEXII
--------------------------------------------------------

  CREATE TABLE "CIMS_ALO_Q_ANNEXII" ("SR_NO" NUMBER, "COUNTRY_CODE" VARCHAR2(3), "BRANCH_CODE" VARCHAR2(20), "ANNEXII" VARCHAR2(300), "DR_NO" NUMBER(20,2), "DR_AMT" NUMBER(20,2), "CR_NO" NUMBER(20,2), "CR_AMT" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table CIMS_ALO_Q_ASSETS1
--------------------------------------------------------

  CREATE TABLE "CIMS_ALO_Q_ASSETS1" ("SR_NO" NUMBER, "COUNTRY_CODE" VARCHAR2(3), "BRANCH_CODE" VARCHAR2(20), "ASSETS" VARCHAR2(300), "ONE_28_DAYS" NUMBER(20,2), "TWO9_DAYS_UPTO_3MNHS" NUMBER(20,2), "OVER_3MNHS_UPTO_6MNHS" NUMBER(20,2), "OVER_6MNHS_UPTO_1YR" NUMBER(20,2), "OVER_1YR_UPTO_3YRS" NUMBER(20,2), "OVER_3YRS_UPTO_5YRS" NUMBER(20,2), "OVER_5YRS" NUMBER(20,2), "NON_SENS" NUMBER(20,2), "TOTAL" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table CIMS_ALO_Q_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_ALO_Q_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ALO_Q_LIABILITIES1
--------------------------------------------------------

  CREATE TABLE "CIMS_ALO_Q_LIABILITIES1" ("SR_NO" NUMBER, "COUNTRY_CODE" VARCHAR2(3), "BRANCH_CODE" VARCHAR2(20), "LIABILITIES" VARCHAR2(300), "ONE_28_DAYS" NUMBER(20,2), "TWO9_DAYS_UPTO_3MNHS" NUMBER(20,2), "OVER_3MNHS_UPTO_6MNHS" NUMBER(20,2), "OVER_6MNHS_UPTO_1YR" NUMBER(20,2), "OVER_1YR_UPTO_3YRS" NUMBER(20,2), "OVER_3YRS_UPTO_5YRS" NUMBER(20,2), "OVER_5YRS" NUMBER(20,2), "NON_SENS" NUMBER(20,2), "TOTAL" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table CIMS_ALO_Q_OTHER_PROD1
--------------------------------------------------------

  CREATE TABLE "CIMS_ALO_Q_OTHER_PROD1" ("SR_NO" NUMBER, "COUNTRY_CODE" VARCHAR2(3), "BRANCH_CODE" VARCHAR2(20), "OTHER_PROD" VARCHAR2(300), "ONE_28_DAYS" NUMBER(20,4), "TWO9_DAYS_UPTO_3MNHS" NUMBER(20,4), "OVER_3MNHS_UPTO_6MNHS" NUMBER(20,4), "OVER_6MNHS_UPTO_1YR" NUMBER(20,4), "OVER_1YR_UPTO_3YRS" NUMBER(20,4), "OVER_3YRS_UPTO_5YRS" NUMBER(20,4), "OVER_5YRS" NUMBER(20,4), "NON_SENS" NUMBER(20,4), "TOTAL" NUMBER(20,4), "RDATE" DATE, "CODE" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table CIMS_ALO_Q_SIGNATORY
--------------------------------------------------------

  CREATE TABLE "CIMS_ALO_Q_SIGNATORY" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_BBSD_ATM_TRAN
--------------------------------------------------------

  CREATE TABLE "CIMS_BBSD_ATM_TRAN" ("DESCRIPTION" VARCHAR2(200), "NO_OF_TRANS" NUMBER, "CODE" NUMBER, "RDATE" DATE, "VAL_OF_TRANS" NUMBER, "SR_NO" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_BBSD_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_BBSD_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE, "SR_NO" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_BBSD_NO_OF_BRANCHES
--------------------------------------------------------

  CREATE TABLE "CIMS_BBSD_NO_OF_BRANCHES" ("STATE" VARCHAR2(200), "POP_GROUP" VARCHAR2(200), "TYPE_OFFICES" VARCHAR2(200), "PREVIOUS_MONTH" NUMBER, "OPEN_DUR_MONTH" NUMBER, "CLOSE_MONTH" NUMBER, "CURRENT_MONTH" NUMBER, "RDATE" DATE, "SR_NO" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_BBSD_SIGN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_BBSD_SIGN_INFO" ("DESCRIPTION" VARCHAR2(200), "VAL" VARCHAR2(200), "CODE" NUMBER, "RDATE" DATE, "SR_NO" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_BBSD_WLA_1
--------------------------------------------------------

  CREATE TABLE "CIMS_BBSD_WLA_1" ("STATE" VARCHAR2(200), "POP_GROUP" VARCHAR2(200), "TYPE_OFFICES" VARCHAR2(200), "TIER" VARCHAR2(200), "PREVIOUSR_MONTH" NUMBER, "OPEN_DUR_MONTH" NUMBER, "CLOSE_MONTH" NUMBER, "CURRENT_MONTH" NUMBER, "RDATE" DATE, "SR_NO" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_BBSD_WLA_2
--------------------------------------------------------

  CREATE TABLE "CIMS_BBSD_WLA_2" ("DESCRIPTION" VARCHAR2(200), "NO_OF_TRANS" NUMBER, "CODE" NUMBER, "RDATE" DATE, "VAL_OF_TRANS" NUMBER, "SR_NO" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_BSA_Y_ASSET_QUAL_LOAN_ADV
--------------------------------------------------------

  CREATE TABLE "CIMS_BSA_Y_ASSET_QUAL_LOAN_ADV" ("DESCRIPTION" VARCHAR2(100), "VALUE" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_BSA_Y_ASST_LIAB
--------------------------------------------------------

  CREATE TABLE "CIMS_BSA_Y_ASST_LIAB" ("DESCRIPTION" VARCHAR2(100), "VALUE" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_BSA_Y_CKF
--------------------------------------------------------

  CREATE TABLE "CIMS_BSA_Y_CKF" ("DESCRIPTION" VARCHAR2(100), "VALUE" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_BSA_Y_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_BSA_Y_GEN_INFO" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_BSA_Y_LCR_DISCLO
--------------------------------------------------------

  CREATE TABLE "CIMS_BSA_Y_LCR_DISCLO" ("DESCRIPTION" VARCHAR2(100), "TOTAL_UNWEIGHTED" NUMBER(20,2), "TOTAL_WEIGHTED" NUMBER(20,4), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_BSA_Y_PROFILE
--------------------------------------------------------

  CREATE TABLE "CIMS_BSA_Y_PROFILE" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(500), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_BSA_Y_PUBLIC_ISSUE
--------------------------------------------------------

  CREATE TABLE "CIMS_BSA_Y_PUBLIC_ISSUE" ("DATE_ISSUE" VARCHAR2(20), "EQUITY_CAP" NUMBER(20,2), "TOTAL_SIZE_EQUITY" NUMBER(20,2), "TOTAL_SIZE_PREMIUM" NUMBER(20,2), "TOTAL" NUMBER(20,2), "EQUITY_CAP_AFTER_ISSUE" NUMBER(20,2), "POST_ISSUE_GOVT_RBI" NUMBER(20,2), "POST_ISSUE_GOVT_RBI_PERCENT" NUMBER(20,4), "POST_ISSUE_OTHERS" NUMBER(20,2), "POST_ISSUE_OTHERS_PERCENT" NUMBER(20,4), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_BSA_Y_PUBLIC_ISSUE_DIVI_P
--------------------------------------------------------

  CREATE TABLE "CIMS_BSA_Y_PUBLIC_ISSUE_DIVI_P" ("DESCRIPTION" VARCHAR2(100), "VALUE" NUMBER(20,4), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_BSA_Y_P_AND_L
--------------------------------------------------------

  CREATE TABLE "CIMS_BSA_Y_P_AND_L" ("DESCRIPTION" VARCHAR2(100), "VALUE" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_BSA_Y_QUANTUM_NPAS
--------------------------------------------------------

  CREATE TABLE "CIMS_BSA_Y_QUANTUM_NPAS" ("SIZE_OF_NPAS" VARCHAR2(100), "NUMBER_OF_ACCOUNTS" NUMBER(30), "AMOUNT_INVOLVED" NUMBER(30,2), "PERCENT_TOTAL_GROSS_NPAS" NUMBER(30,4), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_BSA_Y_SCH1
--------------------------------------------------------

  CREATE TABLE "CIMS_BSA_Y_SCH1" ("DESCRIPTION" VARCHAR2(100), "VALUE" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_BSA_Y_SCH10_11_12
--------------------------------------------------------

  CREATE TABLE "CIMS_BSA_Y_SCH10_11_12" ("DESCRIPTION" VARCHAR2(100), "VALUE" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_BSA_Y_SCH13_14_15_16
--------------------------------------------------------

  CREATE TABLE "CIMS_BSA_Y_SCH13_14_15_16" ("DESCRIPTION" VARCHAR2(500), "VALUE" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_BSA_Y_SCH1_CAP_DETAIL
--------------------------------------------------------

  CREATE TABLE "CIMS_BSA_Y_SCH1_CAP_DETAIL" ("DESCRIPTION" VARCHAR2(100), "NUMBER_OF_SHARES" NUMBER(30), "AMOUNT_OF_SHARES" NUMBER(30,2), "TOTAL" NUMBER(30,2), "CODE" NUMBER(20), "TYPEID" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_BSA_Y_SCH2
--------------------------------------------------------

  CREATE TABLE "CIMS_BSA_Y_SCH2" ("DESCRIPTION" VARCHAR2(100), "VALUE" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_BSA_Y_SCH3_4_5
--------------------------------------------------------

  CREATE TABLE "CIMS_BSA_Y_SCH3_4_5" ("DESCRIPTION" VARCHAR2(100), "VALUE" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_BSA_Y_SCH6_7
--------------------------------------------------------

  CREATE TABLE "CIMS_BSA_Y_SCH6_7" ("DESCRIPTION" VARCHAR2(100), "VALUE" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_BSA_Y_SCH8_9
--------------------------------------------------------

  CREATE TABLE "CIMS_BSA_Y_SCH8_9" ("DESCRIPTION" VARCHAR2(100), "VALUE" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_BSA_Y_SIGN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_BSA_Y_SIGN_INFO" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_BSA_Y_SUITS
--------------------------------------------------------

  CREATE TABLE "CIMS_BSA_Y_SUITS" ("DESCRIPTION" VARCHAR2(100), "SUIT_FILE_NO" NUMBER(30), "SUIT_FILE_AMT" NUMBER(30,2), "DECREED_ACC_NO" NUMBER(30), "DECREED_ACC_AMT" NUMBER(30,2), "DECREED_ACC_AMT_RECOV" NUMBER(30,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_ADV_INVST_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_ADV_INVST_GEN_INFO" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_ADV_INVST_PROFORMA_I
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_ADV_INVST_PROFORMA_I" ("SRNO" NUMBER, "DIRECTORNAME" VARCHAR2(200), "BORROWERNAME" VARCHAR2(200), "RELATIONSHIP" VARCHAR2(200), "DATEOFSANCTION" VARCHAR2(200), "TYPEOFFACILITYFUNDED" NUMBER(20,2), "TYPEOFFACILITYNONFUNDED" NUMBER(20,2), "SECURED" NUMBER(20,2), "UNSECURED" NUMBER(20,2), "NATUREOFSECURITY" VARCHAR2(200), "VALUEOFSECURITY" NUMBER(20,2), "DUEDATE" VARCHAR2(200), "OUSTANDINGSECURED" NUMBER(20,2), "OUSTANDINGUNSECURED" NUMBER(20,2), "AMTTYPE" VARCHAR2(200), "TOTALOUTSTANDING" NUMBER(20,2), "EXPSOURESANCTIONED" NUMBER(20,2), "EXPOSURENORM" VARCHAR2(200), "ACTIONS" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_ADV_INVST_PROFORMA_II
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_ADV_INVST_PROFORMA_II" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(500), "VALUE" NUMBER(20,4), "DRCTV_VOILTED_Y_N" VARCHAR2(10), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_ADV_INVST_PROFORMA_I_T
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_ADV_INVST_PROFORMA_I_T" ("DESCRIPTION" VARCHAR2(50), "TYPEOFFACILITYFUNDED" NUMBER(20,2), "TYPEOFFACILITYNONFUNDED" NUMBER(20,2), "SECURED" NUMBER(20,2), "UNSECURED" NUMBER(20,2), "OUSTANDINGSECURED" NUMBER(20,2), "OUSTANDINGUNSECURED" NUMBER(20,2), "TOTALOUTSTANDING" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_ADV_INVST_SHARES_DEB
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_ADV_INVST_SHARES_DEB" ("SRNO" NUMBER, "NAMEOFBORROWER" VARCHAR2(200), "PAN" VARCHAR2(200), "STATUS" VARCHAR2(200), "DATEOFADVANCE" VARCHAR2(200), "TYPEOFSECURITY" VARCHAR2(200), "NATUREOFCREDITFACILITY" VARCHAR2(200), "AMOUNTSANCTIONED" NUMBER(20,2), "OUTSTANDINGBALANCE" NUMBER(20,2), "MARKETVALUE" NUMBER(20,2), "WHETHERPHYSICALFORM" VARCHAR2(200), "DUEDATE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_ADV_INVST_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_ADV_INVST_SIGN" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_ADV_INVST_UCB
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_ADV_INVST_UCB" ("SR_NO" NUMBER, "NAMEOFBANK" VARCHAR2(200), "CATEGORY" VARCHAR2(200), "NATURE" VARCHAR2(200), "DATEOFINVEST" VARCHAR2(200), "AMOUNT" NUMBER(20,2), "ROI" NUMBER(20,4), "DATEOFMATURITY" VARCHAR2(200), "NOOFRCSPERMISSIONS" NUMBER, "DATERCSPERMISSIONS" VARCHAR2(200), "REMARKS" VARCHAR2(200), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_ALM_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_ALM_GEN_INFO" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "FREQ" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_ALM_IRSS
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_ALM_IRSS" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(300), "UPTO_3M" NUMBER(20,4), "OVER_3M_AND_UPTO_6M" NUMBER(20,4), "OVER_6M_AND_UPTO_1Y" NUMBER(20,4), "OVER_1Y_AND_UPTO_3Y" NUMBER(20,4), "OVER_3Y_AND_UPTO_5Y" NUMBER(20,4), "OVER_5Y" NUMBER(20,4), "NON_SENSITIVE" NUMBER(20,4), "TOTAL" NUMBER(20,4), "CODE" NUMBER(20), "RDATE" DATE, "FREQ" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_ALM_SIG_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_ALM_SIG_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(300), "VALUE" VARCHAR2(100), "CODE" NUMBER(20), "RDATE" DATE, "FREQ" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_ALM_SLS_NON_SCHL
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_ALM_SLS_NON_SCHL" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(300), "D1_TO_14D" NUMBER(20,4), "D15_TO_28D" NUMBER(20,4), "D29_AND_UPTO_3M" NUMBER(20,4), "OVER_3M_AND_UPTO_6M" NUMBER(20,4), "OVER_6M_AND_UPTO_1Y" NUMBER(20,4), "OVER_1Y_AND_UPTO_3Y" NUMBER(20,4), "OVER_3Y_AND_UPTO_5Y" NUMBER(20,4), "OVER_5Y" NUMBER(20,4), "TOTAL" NUMBER(20,4), "CODE" NUMBER(20), "RDATE" DATE, "FREQ" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_ALM_SLS_SCHL
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_ALM_SLS_SCHL" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(300), "D1" NUMBER(20,4), "D2_TO_7D" NUMBER(20,4), "D8_TO_14D" NUMBER(20,4), "D15_TO_28D" NUMBER(20,4), "D29_TO_3M" NUMBER(20,4), "OVER_3M_AND_UPTO_6M" NUMBER(20,4), "OVER_6M_AND_UPTO_1Y" NUMBER(20,4), "OVER_1Y_AND_UPTO_3Y" NUMBER(20,4), "OVER_3Y_AND_UPTO_5Y" NUMBER(20,4), "OVER_5Y" NUMBER(20,4), "TOTAL" NUMBER(20,4), "CODE" NUMBER(20), "RDATE" DATE, "FREQ" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_ALM_TD_AMT_DEP_T1
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_ALM_TD_AMT_DEP_T1" ("SR_NO" NUMBER, "TENOR_SZ_OF_DEP" VARCHAR2(300), "UP28D_TOT" NUMBER(20,4), "UP28D_WEIGHT" NUMBER(20,4), "D29_AND_UPTO_90D_TOT" NUMBER(20,4), "D29_AND_UPTO_90D_WEIGHT" NUMBER(20,4), "D91_AND_UPTO_180D_TOT" NUMBER(20,4), "D91_AND_UPTO_180D_WEIGHT" NUMBER(20,4), "D181_AND_UPTO_1Y_TOT" NUMBER(20,4), "D181_AND_UPTO_1Y_WEIGHT" NUMBER(20,4), "MORE_1Y_AND_UPTO_3Y_TOT" NUMBER(20,4), "MORE_1Y_AND_UPTO_3Y_WEIGHT" NUMBER(20,4), "MORE_3Y_AND_UPTO_5Y_TOT" NUMBER(20,4), "MORE_3Y_AND_UPTO_5Y_WEIGHT" NUMBER(20,4), "MORE_5Y_TOT" NUMBER(20,4), "MORE_5Y_WEIGHT" NUMBER(20,4), "TOTAL_TOL" NUMBER(20,4), "TOTAL_WEIGHT" NUMBER(20,4), "CODE" NUMBER(20), "RDATE" DATE, "FREQ" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_ALM_TD_AMT_DEP_T2
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_ALM_TD_AMT_DEP_T2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(300), "CURRENT_DEP" NUMBER(20,4), "SAVINGS_DEP" NUMBER(20,4), "TERM_DEP" NUMBER(20,4), "TOTAL" NUMBER(20,4), "REMARK" VARCHAR2(100), "CODE" NUMBER(20), "RDATE" DATE, "FREQ" VARCHAR2(20), "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_CLASSI_T1
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_CLASSI_T1" ("SRNO" NUMBER, "RISK_CATEGORY" VARCHAR2(200), "GROSS_LOANS_AND_ADVANCES_OUT" NUMBER(20,2), "PROVISIONS_OR_DEDUCTIONS" NUMBER(20,2), "NET_LOANS_AND_ADVANCES_OUT" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_CLASSI_T2
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_CLASSI_T2" ("SRNO" NUMBER, "NETTING_ITEMS_FOR_NPAS" VARCHAR2(200), "AMOUNT" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_CLASSI_T3
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_CLASSI_T3" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "AMOUNT" VARCHAR2(20), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_CLASSI_T4
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_CLASSI_T4" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "AMOUNT" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_EXPO_LIM_1_T1
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_EXPO_LIM_1_T1" ("SRNO" NUMBER, "CAPITAL_POSITION" VARCHAR2(200), "AMOUNT" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_EXPO_LIM_1_T2
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_EXPO_LIM_1_T2" ("SRNO" NUMBER, "PAN_OF_BORROWER" VARCHAR2(200), "NAME_OF_BORROWER" VARCHAR2(200), "FUNDED" NUMBER(20,2), "NON_FUNDED" NUMBER(20,2), "LIMIT_SANCTIONED" NUMBER(20,2), "PER_TO_TOTAL_ADVANCES" NUMBER(20,4), "OUTSTANDING_BALANCE" NUMBER(20,2), "PER_TO_TIER_1_CAPITAL" NUMBER(20,4), "ASSET_CLASSIFICATION" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_EXPO_LIM_2
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_EXPO_LIM_2" ("SRNO" NUMBER, "NAME_OF_GROUP_BORROWER" VARCHAR2(200), "FUNDED" NUMBER(20,2), "NON_FUNDED" NUMBER(20,2), "LIMIT_SANCTIONED" NUMBER(20,2), "PER_TO_TOTAL_ADVANCES" NUMBER(20,4), "OUTSTANDING_BALANCE" NUMBER(20,2), "PER_TO_TIER_1_CAPITAL" NUMBER(20,4), "ASSET_CLASSIFICATION" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_EXPO_LIM_3
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_EXPO_LIM_3" ("SRNO" NUMBER, "COUNTER_PARTY_BANK" VARCHAR2(200), "FUNDED_EXPOSURE" NUMBER(20,2), "NON_FUNDED_EXPOSURE" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_FILING_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_FILING_INFO" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_INDUS_BRKUP_T1
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_INDUS_BRKUP_T1" ("SRNO" NUMBER, "INDUSTRY_NAME" VARCHAR2(200), "GROSS_LOANS_AND_ADVANCES" NUMBER(20,2), "SUB_STD_GROSS_NPAS" NUMBER(20,2), "DOUBTFUL_GROSS_NPAS" NUMBER(20,2), "LOSS_GROSS_NPAS" NUMBER(20,2), "TOTAL_GROSS_NPAS" NUMBER(20,2), "SUB_STD_PROV_MADE" NUMBER(20,2), "DOUBTFUL_PROV_MADE" NUMBER(20,2), "LOSS_PROV_MADE" NUMBER(20,2), "TOTAL_PROV_MADE" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20), "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_MEMO_ITEM
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_MEMO_ITEM" ("SRNO" NUMBER, "MEMORANDUM_ITEM" VARCHAR2(200), "CURRENT_QUARTER" NUMBER(20,2), "APRIL_TO_DATE" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_MOVMT_T1
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_MOVMT_T1" ("SRNO" NUMBER, "MOVEMENT_FROM" VARCHAR2(4000), "STANDARD" NUMBER(20,2), "SUB_STANDARD" NUMBER(20,2), "DOUBTFUL" NUMBER(20,2), "LOSS" NUMBER(20,2), "TOTAL" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_MOVMT_T2
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_MOVMT_T2" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(600), "SUB_STANDARD" NUMBER(20,2), "DOUBTFUL" NUMBER(20,2), "LOSS" NUMBER(20,2), "TOTAL" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_MOVMT_T3
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_MOVMT_T3" ("SRNO" NUMBER, "MOV_PROV_FOR_NPAS" VARCHAR2(600), "AMOUNT" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_OTHER_NON_SLR
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_OTHER_NON_SLR" ("SRNO" NUMBER, "CATEGORY_OF_SECURITIES" VARCHAR2(200), "RATED_RATINGWISE" NUMBER(20,2), "UNRATED_RATINGWISE" NUMBER(20,2), "BORROWERS_CATEGORYWISE" NUMBER(20,2), "NON_BORROWERS_CATEGORYWISE" NUMBER(20,2), "RATED_AMT_ACQ_PRIVATE" NUMBER(20,2), "UNRATED_AMT_ACQ_PRIVATE" NUMBER(20,2), "TOTAL_NPIS" NUMBER(20,2), "TOTAL_PROVISIONS" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_PORT_ANAL
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_PORT_ANAL" ("SRNO" NUMBER, "PERIOD_OF_DELINQUENCY" VARCHAR2(200), "LOANS_AND_ADVANCES" NUMBER(20,2), "OVERDRAFTS_AND_CASH_CREDIT" NUMBER(20,2), "BILLS_PURCHASED_AND_DISCOUNTED" NUMBER(20,2), "GROSS_LOAN_AND_ADVANCES" NUMBER(20,2), "COMMERCIAL_PAPER" NUMBER(20,2), "NOTES_AND_BONDS_OF_CORPORATES" NUMBER(20,2), "INTER_BANK_ASSESTS" NUMBER(20,2), "LEASE_RECEIVABLES" NUMBER(20,2), "SLR_INVESTMENTS" NUMBER(20,2), "OTHERS" NUMBER(20,2), "TOTAL_OBIA" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_QLTY_SECURITY
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_QLTY_SECURITY" ("SRNO" NUMBER, "ITEM" VARCHAR2(200), "HELD_TO_MATURITY" NUMBER(20,2), "AVAILABLE_FOR_SALE" NUMBER(20,2), "HELD_FOR_TRADING" NUMBER(20,2), "AVAILABLE_FOR_SALE_MARKET_VAL" NUMBER(20,2), "HELD_FOR_TRADING_MARKET_VAL" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_SEC_CREDIT_T1
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_SEC_CREDIT_T1" ("SRNO" NUMBER, "ITEM" VARCHAR2(200), "GROSS_LOANS_AND_ADVANCES" NUMBER(20,2), "GROSS_NPAS" NUMBER(20,2), "PROVISIONS_MADE" NUMBER(20,2), "RDATE" DATE, "CODE" NUMBER, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_SEC_CREDIT_T2
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_SEC_CREDIT_T2" ("SRNO" NUMBER, "MEMO" VARCHAR2(200), "GROSS_LOANS_AND_ADVANCES" NUMBER(20,2), "GROSS_NPAS" NUMBER(20,2), "PROVISIONS_MADE" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_SEC_CREDIT_T3
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_SEC_CREDIT_T3" ("SRNO" NUMBER, "PRIORITY_SECTOR" VARCHAR2(200), "NO_OF_ACS_OUTSTANDING" NUMBER(20,2), "AMOUNT_OUSTANDING" NUMBER(20,2), "AMOUNT_GROSS_NPAS" NUMBER(20,2), "PROVISIONS_GROSS_NPAS" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_SEN_SECT_T1
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_SEN_SECT_T1" ("SRNO" NUMBER, "CATEGORY" VARCHAR2(200), "GROSS_AMT_OUTSTANDING" NUMBER(20,2), "GROSS_NPAS" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20), "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_SEN_SECT_T3
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_SEN_SECT_T3" ("SRNO" NUMBER, "EXPOSURE_TO_REAL_ESTATE_SEC" VARCHAR2(1000), "AMOUNT_OUTSTANDING" NUMBER(20,2), "GROSS_NPAS" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_SIGNATORY
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_SIGNATORY" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "AUTHORISED_REPO_OFFICAL" VARCHAR2(200), "COUNTER_SIGNED_BY" VARCHAR2(200), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_SORA_OFF_T2
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_SORA_OFF_T2" ("SRNO" NUMBER, "ITEMS_INVOKED" VARCHAR2(4000), "STANDARD" NUMBER(20,2), "SUB_STANDARD" NUMBER(20,2), "DOUBTFUL" NUMBER(20,2), "LOSS" NUMBER(20,2), "TOTAL" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_SORA_ON_T1
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_SORA_ON_T1" ("SRNO" NUMBER, "ITEM" VARCHAR2(4000), "STANDARD" NUMBER(20,2), "SUB_STANDARD" NUMBER(20,2), "DOUBTFUL" NUMBER(20,2), "LOSS" NUMBER(20,2), "TOTAL" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_TIC_T1
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_TIC_T1" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "AMOUNT" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_TIC_T2
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_TIC_T2" ("SRNO" NUMBER, "NO_OF_ACCOUNT_1" NUMBER(20,2), "AMOUNT_INVOLVED_1" NUMBER(20,2), "NO_OF_ACCOUNT_2" NUMBER(20,2), "AMOUNT_INVOLVED_2" NUMBER(20,2), "NO_OF_ACCOUNT_3" NUMBER(20,2), "AMOUNT_INVOLVED_3" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_TIC_T3
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_TIC_T3" ("SRNO" NUMBER, "NO_OF_ACCOUNT_1" NUMBER(20,2), "AMOUNT_INVOLVED_1" NUMBER(20,2), "NO_OF_ACCOUNT_2" NUMBER(20,2), "AMOUNT_INVOLVED_2" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_TIC_T4
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_TIC_T4" ("SRNO" NUMBER, "NO_OF_ACCOUNT_1" NUMBER(20,2), "AMOUNT_INVOLVED_1" NUMBER(20,2), "AMOUNT_RECOVERED_1" NUMBER(20,2), "AMOUNT_OUTSTANDING_1" NUMBER(20,2), "AMOUNT_WRITTENOFF_1" NUMBER(20,2), "NO_OF_ACCOUNT_2" NUMBER(20,2), "AMOUNT_INVOLVED_2" NUMBER(20,2), "AMOUNT_RECOVERED_2" NUMBER(20,2), "AMOUNT_OUTSTANDING_2" NUMBER(20,2), "AMOUNT_WRITTENOFF_2" NUMBER(20,2), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCBS01_TIC_T5
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCBS01_TIC_T5" ("SRNO" NUMBER, "PAN_OF_BORROWER" VARCHAR2(200), "NAME_OF_BORROWER" VARCHAR2(200), "LOANS_AND_ADVANCES" NUMBER(20,2), "INDUSTRY" NUMBER(20,2), "TYPE_OF_CONTI_CREDITS" VARCHAR2(200), "FUNDED" NUMBER(20,2), "NON_FUNDED" NUMBER(20,2), "PER_TO_TOTAL_ADVANCES" NUMBER(20,4), "PER_TO_CAPITAL_FUNDS" NUMBER(20,4), "ASSET_CLASSIFICATION" VARCHAR2(200), "LOSS_PROVISION_HELD" NUMBER(20,2), "INTEREST_IN_ARREAR" NUMBER(20,2), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCM_AGGREGATES
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCM_AGGREGATES" ("AGGREGATES" VARCHAR2(100), "BORROWED" NUMBER(20,4), "LENT" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCM_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCM_GEN_INFO" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCM_MONEY_OPS
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCM_MONEY_OPS" ("SRNO" NUMBER, "DT" VARCHAR2(100), "BORROWEDAMT" NUMBER(20,2), "BORROWEDRANGEOFINTEREST_MIN" NUMBER(20,4), "BORROWEDRANGEOFINTEREST_MAX" NUMBER(20,4), "LENTAMT" NUMBER(20,2), "LENTRANGEOFINTEREST_MIN" NUMBER(20,4), "LENTRANGEOFINTEREST_MAX" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_DCM_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_DCM_SIGN" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR4_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR4_GEN_INFO" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR4_MAIN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR4_MAIN" ("SRNO" NUMBER, "BRANCHCODE" VARCHAR2(200), "NAMEOFBRANCH" VARCHAR2(200), "BRANCHADDRESS" VARCHAR2(200), "STATE" VARCHAR2(200), "DISTRICT" VARCHAR2(200), "TYPEOFBRANCH" VARCHAR2(200), "RISKCLASSIFICATION" VARCHAR2(200), "CURRENCYCHESTBRANCH" VARCHAR2(200), "NOOFARMEDGUARDS" NUMBER, "TYPEOFCASE" VARCHAR2(200), "PLACEOFOCCURRENCE" VARCHAR2(200), "DATEANDTIMEOFOCCURRENCE" VARCHAR2(200), "AMOUNTINVOLVED" NUMBER(20,2), "AMOUNTRECOVERED" NUMBER(20,2), "INSURANCECLAIMSETTLED" NUMBER(20,2), "STAFFARRESTED" NUMBER, "ROBBERSARRESTED" NUMBER, "STAFFKILLED" NUMBER, "ROBBERSKILLED" NUMBER, "OTHERSKILLED" NUMBER, "STAFFINJURED" NUMBER, "OTHERSINJURED" NUMBER, "STAFFCONVICTED" NUMBER, "ROBBERSCONVICTED" NUMBER, "COMPENSATIONPAIDTOSTAFF" NUMBER(20,2), "COMPENSATIONPAIDTOOTHERS" NUMBER(20,2), "ACTIONTAKEN" VARCHAR2(200), "CRIMENOPOLICESTATIONNAME" VARCHAR2(200), "MODUSOPERANDI" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR4_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR4_SIGN" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_ASSETS_LYT1
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_ASSETS_LYT1" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_ASSETS_LYT1_YEAR
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_ASSETS_LYT1_YEAR" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_ASSETS_LYT2
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_ASSETS_LYT2" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_ASSETS_LYT2_YEAR
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_ASSETS_LYT2_YEAR" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_ASSETS_LYT3
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_ASSETS_LYT3" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_ASSETS_LYT3_YEAR
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_ASSETS_LYT3_YEAR" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_ASSETS_LYT4
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_ASSETS_LYT4" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_ASSETS_LYT4_YEAR
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_ASSETS_LYT4_YEAR" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_ASSETS_LYT5
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_ASSETS_LYT5" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_ASSETS_LYT5_YEAR
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_ASSETS_LYT5_YEAR" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_DEMAND
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_DEMAND" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_DEMAND_YEAR
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_DEMAND_YEAR" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_FUND_RSRV
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_FUND_RSRV" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_FUND_RSRV_YEAR
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_FUND_RSRV_YEAR" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_GEN_INFO" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_GEN_INFO_YEAR
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_GEN_INFO_YEAR" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_LIABILITIES
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_LIABILITIES" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_LIABILITIES_YEAR
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_LIABILITIES_YEAR" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_OTHRDEMAND
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_OTHRDEMAND" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_OTHRDEMAND_YEAR
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_OTHRDEMAND_YEAR" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_OTHRINVST
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_OTHRINVST" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_OTHRINVST_YEAR
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_OTHRINVST_YEAR" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_OTHRTIME
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_OTHRTIME" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_OTHRTIME_YEAR
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_OTHRTIME_YEAR" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_SIGN" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_SIGN_YEAR
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_SIGN_YEAR" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_TIME
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_TIME" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FMR_IX_TIME_YEAR
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FMR_IX_TIME_YEAR" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORM6SOI_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORM6SOI_GEN_INFO" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORM6SOI_OFFICES
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORM6SOI_OFFICES" ("SRNO" NUMBER, "BRANCH" VARCHAR2(200), "ADDRESSOFBRANCHES" VARCHAR2(200), "STATE" VARCHAR2(200), "DISTRICT" VARCHAR2(200), "BLOCK" VARCHAR2(200), "TALUK" VARCHAR2(200), "POPULATION" VARCHAR2(200), "OFFICETYPE" VARCHAR2(200), "OPENINGDATEOFOFFICE" VARCHAR2(200), "CLOSINGDATEOFOFFICE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORM6SOI_SIGNATORIES
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORM6SOI_SIGNATORIES" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORMB_BORR
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORMB_BORR" ("SR_NO" NUMBER, "BORROWINGS" VARCHAR2(200), "VAL" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORMB_BORR_HM
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORMB_BORR_HM" ("SR_NO" NUMBER, "BORROWINGS" VARCHAR2(200), "VAL" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORMB_GENINFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORMB_GENINFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORMB_GENINFO_HM
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORMB_GENINFO_HM" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORMB_MAIN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORMB_MAIN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "VAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORMB_MAIN_HM
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORMB_MAIN_HM" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "VAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORMB_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORMB_SIGN" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORMB_SIGN_HM
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORMB_SIGN_HM" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORM_II_GENINFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORM_II_GENINFO" ("SRNO" NUMBER(20), "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORM_II_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORM_II_SIGN" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORM_II_UNSECURED_ADV
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORM_II_UNSECURED_ADV" ("SRNO" NUMBER, "NAME_OF_DIREC" VARCHAR2(200), "NAME_OF_COMP" VARCHAR2(200), "RELATION_OF_DIRE" VARCHAR2(200), "AMT_LIMIT_SANC" NUMBER(20,2), "DATE_ADVANCE" VARCHAR2(20), "PURPOSE_ADVANCE" VARCHAR2(200), "DATE_REPAYMENT" VARCHAR2(200), "AMOUNT_OUTSTANDING" NUMBER(20,2), "LOWEST_OUTSTANDING" NUMBER(20,2), "RATE_INTEREST" NUMBER(20,4), "NATURE_ADVANCE" VARCHAR2(200), "REMARKS" VARCHAR2(200), "RDATE" DATE, "UNIQUE_TRANS_NO" NUMBER(20));

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORM_I_CRR_NS
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORM_I_CRR_NS" ("SR_NO" VARCHAR2(20), "CRR_DATE" VARCHAR2(200), "NET_DEMAND_TIME_LIAB" NUMBER(20,2), "CRR_REQ_TO_BE_MAINTAIN" NUMBER(20,2), "CRR_ACTUALLY_MAINTAIN" NUMBER(20,2), "CRR_DEFICIT" NUMBER(20,2), "CRR_SURPLUS" NUMBER(20,2), "CRR_INTEREST" NUMBER(20,2), "REMARKS" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORM_I_GENINFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORM_I_GENINFO" ("SR_NO" NUMBER(20), "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORM_I_PARTA
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORM_I_PARTA" ("SR_NO" VARCHAR2(20), "PARTA" VARCHAR2(200), "FIRST_ALTER_FRIDAY" NUMBER(20,2), "SECOND_ALTER_FRIDAY" NUMBER(20,2), "THIRD_ALTER_FRIDAY" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORM_I_PARTA_II_C
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORM_I_PARTA_II_C" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(200), "FIRST_ALTER_FRIDAY" NUMBER(20,2), "SECOND_ALTER_FRIDAY" NUMBER(20,2), "THIRD_ALTER_FRIDAY" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORM_I_PARTC_XII_C
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORM_I_PARTC_XII_C" ("SR_NO" VARCHAR2(20), "PARTICULARS" VARCHAR2(200), "FIRST_ALT_FIRDAY_FV" NUMBER(20,2), "FIRST_ALT_FIRDAY_BV" NUMBER(20,2), "FIRST_ALT_FIRDAY_DEP" NUMBER(20,2), "FIRST_ALT_FIRDAY_NV" NUMBER(20,2), "SECOND_ALT_FIRDAY_FV" NUMBER(20,2), "SECOND_ALT_FIRDAY_BV" NUMBER(20,2), "SECOND_ALT_FIRDAY_DEP" NUMBER(20,2), "SECOND_ALT_FIRDAY_NV" NUMBER(20,2), "THIRD_ALT_FIRDAY_FV" NUMBER(20,2), "THIRD_ALT_FIRDAY_BV" NUMBER(20,2), "THIRD_ALT_FIRDAY_DEP" NUMBER(20,2), "THIRD_ALT_FIRDAY_NV" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORM_I_PARTD
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORM_I_PARTD" ("SR_NO" NUMBER, "PART_D_COMPLIANCE" VARCHAR2(200), "FIRST_ALTER_FRIDAY" NUMBER(20,2), "SECOND_ALTER_FRIDAY" NUMBER(20,2), "FRIDAY_ALTER_FRIDAY" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORM_I_PARTD_XIV_E
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORM_I_PARTD_XIV_E" ("SR_NO" VARCHAR2(20), "PARTICULARS" VARCHAR2(200), "FIRST_ALT_FIRDAY_FV" NUMBER(20,2), "FIRST_ALT_FIRDAY_BV" NUMBER(20,2), "FIRST_ALT_FIRDAY_DEP" NUMBER(20,2), "FIRST_ALT_FIRDAY_NV" NUMBER(20,2), "SECOND_ALT_FIRDAY_FV" NUMBER(20,2), "SECOND_ALT_FIRDAY_BV" NUMBER(20,2), "SECOND_ALT_FIRDAY_DEP" NUMBER(20,2), "SECOND_ALT_FIRDAY_NV" NUMBER(20,2), "THIRD_ALT_FIRDAY_FV" NUMBER(20,2), "THIRD_ALT_FIRDAY_BV" NUMBER(20,2), "THIRD_ALT_FIRDAY_DEP" NUMBER(20,2), "THIRD_ALT_FIRDAY_NV" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORM_I_PART_B_C
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORM_I_PART_B_C" ("SR_NO" NUMBER, "PART_B_COMPLIANCE" VARCHAR2(200), "FIRST_ALTER_FRIDAY" NUMBER(20,2), "SECOND_ALTER_FRIDAY" NUMBER(20,2), "THIRD_ALTER_FRIDAY" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORM_I_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORM_I_SIGN" ("SR_NO" NUMBER(20), "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORM_I_SLR_NS
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORM_I_SLR_NS" ("SR_NO" VARCHAR2(20), "SLR_DATE" VARCHAR2(200), "NET_DEMAND_TIME_LIAB" NUMBER(20,2), "SLR_REQ_TO_BE_MAINTAIN" NUMBER(20,2), "SLR_ACTUALLY_MAINTAIN" NUMBER(20,2), "SLR_DEFICIT" NUMBER(20,2), "SLR_SURPLUS" NUMBER(20,2), "SLR_INTEREST" NUMBER(20,2), "REMARKS" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORM_I_SLR_SCH
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORM_I_SLR_SCH" ("SR_NO" VARCHAR2(20), "SLR_DATE" VARCHAR2(200), "NET_DEMAND_TIME_LIAB" NUMBER(20,2), "SLR_REQ_TO_BE_MAINTAIN" NUMBER(20,2), "SLR_ACTUALLY_MAINTAIN" NUMBER(20,2), "SLR_DEFICIT" NUMBER(20,2), "SLR_SURPLUS" NUMBER(20,2), "SLR_INTEREST" NUMBER(20,2), "REMARKS" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORM_VIII_GENINFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORM_VIII_GENINFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORM_VIII_MAIN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORM_VIII_MAIN" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(200), "NO_OF_AC_CURRENT" NUMBER, "AMOUNT_CURRENT" NUMBER, "NO_OF_AC_SAVING" NUMBER, "AMOUNT_SAVING" NUMBER, "NO_OF_AC_FIX" NUMBER, "AMOUNT_FIX" NUMBER, "NO_OF_AC_OD" NUMBER, "AMOUNT_OD" NUMBER, "NO_OF_AC_TOTAL" NUMBER, "AMOUNT_TOTAL" NUMBER, "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_FORM_VIII_SIGNINFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_FORM_VIII_SIGNINFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_MIS_DEFAULT_SUIT
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_MIS_DEFAULT_SUIT" ("SRNO" NUMBER, "NAMEOFBRANCH" VARCHAR2(100), "BRANCHCODE" VARCHAR2(100), "COMPANYNAME" VARCHAR2(100), "PAN" VARCHAR2(100), "ADDRS" VARCHAR2(100), "DIRECTORNAME" VARCHAR2(100), "DIN" VARCHAR2(100), "TYPEOFFACILITY" VARCHAR2(100), "WILLFULDEFAULTER" VARCHAR2(100), "LIMIT" NUMBER(20,2), "AMOUNT" NUMBER(20,2), "NATUREOFSECURITY" VARCHAR2(100), "VALUEOFSECURITY" NUMBER(20,2), "ASSET" VARCHAR2(100), "DATEOFCLASSIFICATION" VARCHAR2(100), "ACTIONTAKEN" VARCHAR2(100), "REASONS" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_MIS_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_MIS_GEN_INFO" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_MIS_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_MIS_SIGN" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS1_ANNEX1_T1
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS1_ANNEX1_T1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS1_ANNEX1_T2
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS1_ANNEX1_T2" ("SRNO" NUMBER, "NAMEOFBANK" VARCHAR2(200), "AMTOF_DEPOSIT" NUMBER(20,2), "RATEOFINTEREST" NUMBER(20,4), "DATEOFRECEIPT" VARCHAR2(20), "PERIODINDATE" NUMBER(20), "PERIODINMONTHS" NUMBER(20), "PERIODINYEARS" NUMBER(20), "MATURITYDATE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS1_ANNEX1_T3
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS1_ANNEX1_T3" ("SR_NO" NUMBER, "TIME_PERIOD" VARCHAR2(200), "NO_OF_DEBIT_ENTRIES" NUMBER, "AMOUNT_OF_DEBIT_ENTRIES" NUMBER(20,2), "NO_OF_CREDIT_ENTRIES" NUMBER, "AMOUNT_OF_CREDIT_ENTRIES" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS1_ANNEX1_T4
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS1_ANNEX1_T4" ("SR_NO" NUMBER, "TIME_PERIOD" VARCHAR2(200), "NO_OF_DEBIT_ENTRIES" NUMBER, "AMOUNT_OF_DEBIT_ENTRIES" NUMBER(20,2), "NO_OF_CREDIT_ENTRIES" NUMBER, "AMOUNT_OF_CREDIT_ENTRIES" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS1_ANNEX1_T5
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS1_ANNEX1_T5" ("SR_NO" NUMBER, "NAME_OF_BORROWER" VARCHAR2(200), "NAME_OF_BENEFICIARY" VARCHAR2(200), "AMOUNT_OUTSTANDING_AS_ON" NUMBER, "TRANSACTION_ID" VARCHAR2(200), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS1_ANNEX2_T1
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS1_ANNEX2_T1" ("SR_NO" NUMBER, "DUE_FROM_NAME" VARCHAR2(200), "AMOUNT_DUE" NUMBER(20,2), "PROVISION_MADE" NUMBER(20,2), "TRANS_ID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS1_ANNEX2_T2
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS1_ANNEX2_T2" ("SR_NO" NUMBER, "DUE_FROM_NAME" VARCHAR2(200), "AMOUNT_DUE" NUMBER(20,2), "PROVISION_MADE" NUMBER(20,2), "TRANS_ID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS1_ANNEX2_T3
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS1_ANNEX2_T3" ("SR_NO" NUMBER, "DUE_FROM_NAME" VARCHAR2(200), "AMOUNT_DUE_" NUMBER(20,2), "PROVISION_MADE" NUMBER(20,2), "TRANS_ID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS1_ANNEX2_T4
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS1_ANNEX2_T4" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS1_ASSET
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS1_ASSET" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS1_GENINFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS1_GENINFO" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS1_LIAB
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS1_LIAB" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS1_MEMO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS1_MEMO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS1_SIGNATORY
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS1_SIGNATORY" ("SR_NO" NUMBER, "AUTHORISED_REPORTING_OFFICIAL" VARCHAR2(200), "DESCRIPTION" VARCHAR2(200), "COUNTER_SIGNED_BY" VARCHAR2(200), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS2_EARN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS2_EARN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS2_GENINFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS2_GENINFO" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS2_INT_REC
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS2_INT_REC" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS2_OTH_OE_TYPE
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS2_OTH_OE_TYPE" ("SR_NO" NUMBER, "DESCR" VARCHAR2(200), "VAL" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS2_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS2_SIGN" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS3_CLASS_CD_1
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS3_CLASS_CD_1" ("SR_NO" NUMBER, "RISK_CAT" VARCHAR2(200), "GROSS_OS_AMT" NUMBER(20,2), "PROV_DED" NUMBER(20,2), "NET_OS_AMT" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS3_CLASS_CD_2
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS3_CLASS_CD_2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS3_CLASS_CD_3
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS3_CLASS_CD_3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS3_CONS_DATA
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS3_CONS_DATA" ("SR_NO" NUMBER, "PERIOD_OF_DELIQ" VARCHAR2(200), "LA" NUMBER(20,2), "OIBA" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS3_GENINFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS3_GENINFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS3_ORA_OFF_BS
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS3_ORA_OFF_BS" ("SR_NO" NUMBER, "ITEM" VARCHAR2(200), "STANDARD" NUMBER(20,2), "SUB_STANDARD" NUMBER(20,2), "DOUBTFUL" NUMBER(20,2), "LOSS" NUMBER(20,2), "TOTAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS3_ORA_ON_BS
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS3_ORA_ON_BS" ("SR_NO" NUMBER, "ITEM" VARCHAR2(200), "STANDARD" NUMBER(20,2), "SUB_STANDARD" NUMBER(20,2), "DOUBTFUL" NUMBER(20,2), "LOSS" NUMBER(20,2), "TOTAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS3_OTHER_NONSLR
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS3_OTHER_NONSLR" ("SR_NO" NUMBER, "CATEGORY_SEC" VARCHAR2(200), "RATING_DET_RATED" NUMBER(20,2), "RATING_DET_UNRATED" NUMBER(20,2), "CATEGORY_DET_BORRO" NUMBER(20,2), "CATEGORY_DET_NON_BORRO" NUMBER(20,2), "AMT_ACQ_RATED" NUMBER(20,2), "AMT_ACQ_UNRATED" NUMBER(20,2), "TOTAL_NPAS" NUMBER(20,2), "TOTAL_PROVISION" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS3_PA_LA
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS3_PA_LA" ("SR_NO" NUMBER, "PERIOD_OF_DELIQ" VARCHAR2(200), "LOANS" NUMBER(20,2), "OD_CC" NUMBER(20,2), "BILL_PUR_DISC" NUMBER(20,2), "TOT_LOAN_ASSETS" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS3_PA_LA_GROUP
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS3_PA_LA_GROUP" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS3_PA_LA_MEMO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS3_PA_LA_MEMO" ("SR_NO" NUMBER, "MEMO_ITEMS" VARCHAR2(200), "CURR_QUARTER" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS3_PA_LA_OIBA
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS3_PA_LA_OIBA" ("SR_NO" NUMBER, "PERIOD_OF_DELIQ" VARCHAR2(200), "COMM_PAPER" NUMBER(20,2), "NOTES" NUMBER(20,2), "IBA" NUMBER(20,2), "LEASE_REC" NUMBER(20,2), "OTHER_INV" NUMBER(20,2), "TOTAL_OIBA" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS3_QUAL_SEC
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS3_QUAL_SEC" ("SR_NO" NUMBER, "ITEM" VARCHAR2(200), "BV_HELD_TO_MAT" NUMBER(20,2), "BV_AVAIL_FOR_SALE" NUMBER(20,2), "BV_HELD_FOR_TRAD" NUMBER(20,2), "MV_AVAIL_FOR_SALE" NUMBER(20,2), "MV_HELD_FOR_TRAD" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS3_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS3_SIGN" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS4_GENINFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS4_GENINFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS4_PART_A_1
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS4_PART_A_1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" NUMBER(20,4), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS4_PART_A_2
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS4_PART_A_2" ("SR_NO" NUMBER, "QTR_END" VARCHAR2(200), "AMT_NPA_BEG" NUMBER(20,2), "RECOVERIES" NUMBER(20,2), "ADDITION" NUMBER(20,2), "AMT_NPA_END" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS4_PART_A_3
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS4_PART_A_3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS4_PART_B_COMPRO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS4_PART_B_COMPRO" ("SR_NO" NUMBER, "CQ_NO_ACC" NUMBER, "CQ_AMT_INVOLVE" NUMBER(20,2), "CQ_AMT_RECOVER" NUMBER(20,2), "CQ_AMT_OS" NUMBER(20,2), "CQ_AMT_WO" NUMBER(20,2), "APR_DATE_NO_ACC" NUMBER, "APR_DATE_AMT_INVOLVE" NUMBER(20,2), "APR_DATE_AMT_RECOVER" NUMBER(20,2), "APR_DATE_AMT_OS" NUMBER(20,2), "APR_DATE_AMT_WO" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS4_PART_B_EXTEN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS4_PART_B_EXTEN" ("SR_NO" NUMBER, "CQ_NO_ACC" NUMBER, "CQ_AMT" NUMBER(20,2), "APR_DATE_NO_ACC" NUMBER, "APR_DATE_AMT" NUMBER(20,2), "TOT_EXT_NO_ACC" NUMBER, "TOT_EXT_AMT" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS4_PART_B_TOP_50
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS4_PART_B_TOP_50" ("SR_NO" NUMBER, "BORROWERNAME" VARCHAR2(200), "LOANNADVANCES" NUMBER(20,2), "SECTOR" VARCHAR2(200), "TYPEOFCONTINGENTCREDITS" VARCHAR2(200), "TOTFUNDED" NUMBER(20,2), "TOTNONFUNDED" NUMBER, "PERCNTTOTADVANCES" NUMBER(20,4), "PERCENTCAPFUNDS" NUMBER(20,4), "RISKCLASSIFICATION" VARCHAR2(200), "LOSSPROVISION" NUMBER(20,2), "INTEREST" NUMBER(20,2), "BORROWEROFFCPINCODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS4_PART_B_TOP_50_TOT
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS4_PART_B_TOP_50_TOT" ("SR_NO" NUMBER, "DESCRPTION" VARCHAR2(200), "TOTFUNDED" NUMBER(20,2), "TOTNONFUNDED" NUMBER(20,2), "LOSSPROVISION" NUMBER(20,2), "INTEREST" NUMBER(20,2), "RDATE" DATE, "TOT_CREDIT_EXPO" NUMBER(20,2));

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS4_PART_B_WAIVER
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS4_PART_B_WAIVER" ("SR_NO" NUMBER, "CQ_NO_ACC" NUMBER, "CQ_AMT" NUMBER(20,2), "APR_DATE_NO_ACC" NUMBER, "APR_DATE_AMT" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS4_PART_C_1
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS4_PART_C_1" ("SR_NO" NUMBER, "NAMEOFBORROWER" VARCHAR2(200), "TYPEOFFACILITY_FUNDED" NUMBER(20,2), "TYPEOFFACILITY_NONFUNDED" NUMBER(20,2), "LIMIT_SANCTIONED" NUMBER(20,2), "PERCENTTOTOTALADVANCES" NUMBER(20,4), "OUTSTANDINGBALANCE" NUMBER(20,2), "PERCENTTOCAPITALFUNDSOFTHEBANK" NUMBER(20,4), "ASSETCLASSIFICATION" VARCHAR2(200), "BORROWERSHEADOFFICEPINCODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS4_PART_C_2
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS4_PART_C_2" ("SR_NO" NUMBER, "NAMEOFBORROWER" VARCHAR2(200), "TYPEOFFACILITY_FUNDED" NUMBER(20,2), "TYPEOFFACILITY_NONFUNDED" NUMBER(20,2), "LIMIT_SANCTIONED" NUMBER(20,2), "PERCENTTOTOTALADVANCES" NUMBER(20,4), "OUTSTANDINGBALANCE" NUMBER(20,2), "PERCENTTOCAPITALFUNDSOFTHEBANK" NUMBER(20,4), "ASSETCLASSIFICATION" VARCHAR2(200), "BORROWERSHEADOFFICEPINCODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS4_PART_C_3
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS4_PART_C_3" ("SR_NO" NUMBER, "COUNTERPARTYBANK" VARCHAR2(200), "FUNDEDEXPOSURE" NUMBER(20,2), "NONFUNDEDEXPOSURE" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS4_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS4_SIGN" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS5_EXPOSURE
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS5_EXPOSURE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "VAL" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS5_EXPOS_SENSE
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS5_EXPOS_SENSE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS5_GENINFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS5_GENINFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS5_IND_EXPO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS5_IND_EXPO" ("SR_NO" NUMBER, "INDUSTRY_NAME" VARCHAR2(200), "TOTAL_CREDIT_OS" NUMBER(20,2), "IMPAIRED_SUB_STAND" NUMBER(20,2), "IMPAIRED_DOUBTFUL" NUMBER(20,2), "IMPAIRED_LOSS" NUMBER(20,2), "IMPAIRED_TOTAL" NUMBER(20,2), "PROVISION_SUB_STAND" NUMBER(20,2), "PROVISION_DOUBTFUL" NUMBER(20,2), "PROVISION_LOSS" NUMBER(20,2), "PROVISION_TOTAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS5_SEG_WISE_NPS
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS5_SEG_WISE_NPS" ("SR_NO" NUMBER, "PRIORITY_SECTOR" VARCHAR2(200), "OS_NO_ACC" NUMBER, "OS_AMT" NUMBER(20,2), "OS_PERC_TOTAL" NUMBER(20,4), "GROSS_NPA_AMT" NUMBER(20,2), "GROSS_NPA_PERC_TOTAL" NUMBER(20,4), "GROSS_PROVISION" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS5_SEG_WISE_PS
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS5_SEG_WISE_PS" ("SR_NO" NUMBER, "PRIORITY_SECTOR" VARCHAR2(200), "OS_NO_ACC" NUMBER, "OS_AMT" NUMBER(20,2), "OS_PERC_TOTAL" NUMBER(20,4), "GROSS_NPA_AMT" NUMBER(20,2), "GROSS_NPA_PERC_TOTAL" NUMBER(20,4), "GROSS_PROVISION" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS5_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS5_SIGN" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS5_SME
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS5_SME" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS6_AUD_DATE
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS6_AUD_DATE" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS6_AUD_DTL
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS6_AUD_DTL" ("SR_NO" VARCHAR2(20), "TRANSID" VARCHAR2(200), "NAME" VARCHAR2(200), "QUALIFICATIONS" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS6_CR_EXP
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS6_CR_EXP" ("SR_NO" VARCHAR2(20), "TRANSID" VARCHAR2(200), "NAME_DIR" VARCHAR2(200), "NAME_REL_COM_FIRM" VARCHAR2(200), "NATURE_INT" VARCHAR2(200), "REL_DIR" VARCHAR2(200), "TYPE_EXP" VARCHAR2(200), "DATE_EXP" VARCHAR2(200), "AMT_EXP" NUMBER(20,2), "SEC_NATURE" VARCHAR2(200), "SEC_VAL" NUMBER(20,2), "SEC_MARG" NUMBER(20,4), "AMT_OS" NUMBER(20,2), "ASST_CLASS" VARCHAR2(200), "PROVISIONS" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS6_CR_EXP2
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS6_CR_EXP2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS6_CR_EXP_DIR
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS6_CR_EXP_DIR" ("SR_NO" VARCHAR2(20), "TRANSID" VARCHAR2(200), "NAME_ASST_DIR" VARCHAR2(200), "REL_ASST" VARCHAR2(200), "TYPE_EXP" VARCHAR2(200), "AMT_OS_EXP" NUMBER(20,2), "ROI" NUMBER(20,4), "SEC_NATURE" VARCHAR2(200), "SEC_VAL" NUMBER(20,2), "SEC_MARG" NUMBER(20,4), "ASST_CLASS" VARCHAR2(200), "PROVISIONS" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS6_DIR_DTL
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS6_DIR_DTL" ("SR_NO" VARCHAR2(20), "TRANSID" VARCHAR2(200), "NAME" VARCHAR2(200), "QUALIFICATION" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS6_EXP
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS6_EXP" ("SR_NO" VARCHAR2(20), "TRANSID" VARCHAR2(200), "NAME_DIR" VARCHAR2(200), "TYPE_EXP" VARCHAR2(200), "AMT_EXP" NUMBER(20,2), "PERC_EXP" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS6_GENINFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS6_GENINFO" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS6_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS6_SIGN" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS7_CONTRACTS_DRTV
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS7_CONTRACTS_DRTV" ("SRNO" NUMBER, "ITEM" VARCHAR2(200), "NOTIONAL_PRINCIPAL_AMT" NUMBER(20,2), "CONVERSION_FACTOR" NUMBER(20,4), "EQUIVALENT_VALUE" NUMBER(20,2), "RISKWEIGHT" NUMBER(20,4), "RISK_ADJUSTED_VALUE" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS7_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS7_GEN_INFO" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS7_OFF_BS
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS7_OFF_BS" ("SRNO" NUMBER, "ITEMS" VARCHAR2(1000), "GUARANTOR" VARCHAR2(50), "GB_EXP" NUMBER(20,2), "MAV" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "CCF" NUMBER(20,4), "RW" NUMBER(20,4), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS7_ON_BS
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS7_ON_BS" ("SRNO" NUMBER, "ITEMS" VARCHAR2(500), "GBV" NUMBER(20,2), "MAP" NUMBER(20,2), "NET_BV" NUMBER(20,2), "RW" NUMBER(20,4), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS7_ON_BS_OTHER_ASSET
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS7_ON_BS_OTHER_ASSET" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "GROSSBOOKVALUE" NUMBER(20,2), "MARGINANDPROVISION" NUMBER(20,2), "NETBOOKVALUE" NUMBER(20,2), "RISKWEIGHT" NUMBER(20,4), "RISHADJUSTEDVALUE" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS7_RISK_ASSET_RATIO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS7_RISK_ASSET_RATIO" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS7_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS7_SIGN" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS7_WGT_NONFUND
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS7_WGT_NONFUND" ("SRNO" NUMBER, "NATUREOFITEM" VARCHAR2(200), "BOOKVALUE" NUMBER(20,2), "CONVERSION" NUMBER(20,4), "EQUIVALUE" NUMBER(20,2), "RISKWEIGHT" NUMBER(20,4), "ADJUSTEDVALUE" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS8_ATM_PROF
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS8_ATM_PROF" ("SR_NO" VARCHAR2(20), "NAME_ATM" VARCHAR2(200), "ATM_ADD" VARCHAR2(200), "STATE" VARCHAR2(200), "DISTRICT" VARCHAR2(200), "LOCATION" VARCHAR2(200), "ON_OFF_SITE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS8_BRAN_PROF
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS8_BRAN_PROF" ("SR_NO" VARCHAR2(20), "BRANCH_CODE" VARCHAR2(200), "NAME_OFFICE" VARCHAR2(200), "OFFICE_TYPE" VARCHAR2(200), "BRANCH_ADD" VARCHAR2(200), "PINCODE" NUMBER, "STATE" VARCHAR2(200), "DISTRICT" VARCHAR2(200), "DEPOSITS" NUMBER(20,2), "ADVANCES" NUMBER(20,2), "PLAT" NUMBER(20,2), "LOCATION_TYPE" VARCHAR2(20), "FULLY_COMP" VARCHAR2(20), "CBS_IMPL" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS8_DIREC_REM
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS8_DIREC_REM" ("SR_NO" VARCHAR2(20), "NAME_DIREC" VARCHAR2(200), "DATE_REMV" VARCHAR2(20), "ORDER_NO" VARCHAR2(20), "REAS_REMV" VARCHAR2(200), "LEGAL_ACT" VARCHAR2(200), "DATE_ADVC" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS8_EMPLOYEES
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS8_EMPLOYEES" ("DESCRIPTION" VARCHAR2(200), "VALUE" NUMBER(20), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS8_FINL_INCL
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS8_FINL_INCL" ("SR_NO" VARCHAR2(20), "PARTICULARS" VARCHAR2(300), "VALUE" VARCHAR2(20), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS8_FIN_PARAM
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS8_FIN_PARAM" ("SR_NO" VARCHAR2(20), "DESCRIPTION" VARCHAR2(200), "VALUE" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS8_GENINFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS8_GENINFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS8_GEN_PROF
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS8_GEN_PROF" ("SR_NO" VARCHAR2(20), "ITEM" VARCHAR2(200), "PARTICULAR" VARCHAR2(200), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS8_MANG_PROF
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS8_MANG_PROF" ("SR_NO" NUMBER, "EXECUTIVE" VARCHAR2(200), "NAME" VARCHAR2(200), "DESIGNATION" VARCHAR2(200), "IN_BANK" VARCHAR2(50), "TO_INCUMBENT_POSITION" VARCHAR2(50), "LOCATED_AT" VARCHAR2(200), "STDCODE" VARCHAR2(50), "LANDLINE1" NUMBER, "LANDLINE2" NUMBER, "MOBILE" NUMBER, "OFF_EMAIL_ID" VARCHAR2(200), "ALT_EMAIL_ID" VARCHAR2(200), "FAXNO" NUMBER, "ALT_NAME" VARCHAR2(200), "ALT_OFF_EMAIL_ID" VARCHAR2(200), "ALT_MOBILE" NUMBER, "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS8_MANG_PROF_ADRS
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS8_MANG_PROF_ADRS" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS8_NPA_PROF
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS8_NPA_PROF" ("PARTICULAR" VARCHAR2(200), "NO_ACC" NUMBER, "AMT_OUT_PRIN" NUMBER, "AMT_OUT_INT" NUMBER, "PERC_TOT_LOANS_ADV" NUMBER(20,4), "PROVISION_PERC" NUMBER(20,4), "PROVISION_AMT" NUMBER, "EXISTING_PROVISION" NUMBER, "PROV_DURING_YEAR" NUMBER, "TOT_PROVISION" NUMBER, "SHORTFALL_EXCESS" NUMBER, "REMARKS" VARCHAR2(20), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS8_NPA_PROF2
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS8_NPA_PROF2" ("PARTICULAR" VARCHAR2(200), "VALUE" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS8_RATIO_DENO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS8_RATIO_DENO" ("SR_NO" VARCHAR2(20), "FIELD" VARCHAR2(200), "NOTE" VARCHAR2(200), "VALUE" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_OSS8_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_OSS8_SIGN" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_PSA_A_GENINFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_PSA_A_GENINFO" ("SR_NO" NUMBER(20), "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_PSA_A_PARTA_1
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_PSA_A_PARTA_1" ("SR_NO" NUMBER(20), "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_PSA_A_PARTA_2
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_PSA_A_PARTA_2" ("SR_NO" NUMBER(20), "CATEGORIES" VARCHAR2(200), "DISBURS_NO_ACC" NUMBER(20), "DISBURS_AMT" NUMBER(20,2), "DISBURS_LOAN_NO_ACC" NUMBER(20), "DISBURS_LOAN_AMT" NUMBER(20,2), "OUT_NO_ACC" NUMBER(20), "OUT_NO_BENEFICIARIES" NUMBER(20), "OUT_BAL_OUT" NUMBER(20,2), "OUT_LOAN_NO_ACC" NUMBER(20), "OUT_LOAN_NO_BENEFICIARIES" NUMBER(20), "OUT_LOAN_BAL_OUT" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_PSA_A_PARTA_3
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_PSA_A_PARTA_3" ("SR_NO" NUMBER(20), "ITEMS" VARCHAR2(200), "AMT_PURCHASE_DUR_PER" NUMBER(20,2), "AMT_SOLD_DUR_PER" NUMBER(20,2), "NET_AMT" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_PSA_A_PARTB
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_PSA_A_PARTB" ("SR_NO" NUMBER(20), "STATE" VARCHAR2(200), "TOT_NO_ACC" NUMBER(20), "TOT_AMT" NUMBER(20,2), "SC_NO_ACC" NUMBER(20), "SC_AMT" NUMBER(20,2), "ST_NO_ACC" NUMBER(20), "ST_AMT" NUMBER(20,2), "MINORITIES_NO_ACC" NUMBER(20), "MINORITIES_AMT" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_PSA_A_PARTB_FIL_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_PSA_A_PARTB_FIL_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_PSA_A_PARTC
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_PSA_A_PARTC" ("SR_NO" NUMBER(20), "STATE" VARCHAR2(200), "TOT_NO_ACC" NUMBER(20), "TOT_AMT" NUMBER(20,2), "SC_NO_ACC" NUMBER(20), "SC_AMT" NUMBER(20,2), "ST_NO_ACC" NUMBER(20), "ST_AMT" NUMBER(20,2), "MINORITIES_NO_ACC" NUMBER(20), "MINORITIES_AMT" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_PSA_A_PARTC_FIL_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_PSA_A_PARTC_FIL_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_PSA_A_PARTD
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_PSA_A_PARTD" ("SR_NO" NUMBER(20), "STATE" VARCHAR2(200), "CHRIS_NO_ACC" NUMBER(20), "CHRIS_AMT" NUMBER(20,2), "MUS_NO_ACC" NUMBER(20), "MUS_AMT" NUMBER(20,2), "BUDDH_NO_ACC" NUMBER(20), "BUDDH_AMT" NUMBER(20,2), "SIKHS_NO_ACC" NUMBER(20), "SIKHS_AMT" NUMBER(20,2), "ZORO_NO_ACC" NUMBER(20), "ZORO_AMT" NUMBER(20,2), "JAINS_NO_ACC" NUMBER(20), "JAINS_AMT" NUMBER(20,2), "TOT_NO_ACC" NUMBER(20), "TOT_AMT" NUMBER(20,2), "OTH_MINO_NO_ACC" NUMBER(20), "OTH_MINO_AMT" NUMBER(20,2), "TOT_ADV_NO_ACC" NUMBER(20), "TOT_ADV_AMT" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_PSA_A_PARTD_FIL_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_PSA_A_PARTD_FIL_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_PSA_A_PARTE
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_PSA_A_PARTE" ("SR_NO" NUMBER(20), "UT" VARCHAR2(200), "CHRIS_NO_ACC" NUMBER(20), "CHRIS_AMT" NUMBER(20,2), "MUS_NO_ACC" NUMBER(20), "MUS_AMT" NUMBER(20,2), "BUDDH_NO_ACC" NUMBER(20), "BUDDH_AMT" NUMBER(20,2), "SIKHS_NO_ACC" NUMBER(20), "SIKHS_AMT" NUMBER(20,2), "ZORO_NO_ACC" NUMBER(20), "ZORO_AMT" NUMBER(20,2), "JAINS_NO_ACC" NUMBER(20), "JAINS_AMT" NUMBER(20,2), "TOT_NO_ACC" NUMBER(20), "TOT_AMT" NUMBER(20,2), "OTH_MINO_NO_ACC" NUMBER(20), "OTH_MINO_AMT" NUMBER(20,2), "TOT_ADV_NO_ACC" NUMBER(20), "TOT_ADV_AMT" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_PSA_A_PARTE_FIL_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_PSA_A_PARTE_FIL_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_PSA_A_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_PSA_A_SIGN" ("SR_NO" NUMBER(20), "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_PSA_Q_GENINFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_PSA_Q_GENINFO" ("SR_NO" NUMBER(20), "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_PSA_Q_PARTA_1
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_PSA_Q_PARTA_1" ("SR_NO" NUMBER(20), "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_PSA_Q_PARTA_2
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_PSA_Q_PARTA_2" ("SR_NO" NUMBER(20), "CATEGORIES" VARCHAR2(200), "DISBURS_NO_ACC" NUMBER(20), "DISBURS_AMT" NUMBER(20,2), "DISBURS_LOAN_NO_ACC" NUMBER(20), "DISBURS_LOAN_AMT" NUMBER(20,2), "OUT_NO_ACC" NUMBER(20), "OUT_NO_BENEFICIARIES" NUMBER(20), "OUT_BAL_OUT" NUMBER(20,2), "OUT_LOAN_NO_ACC" NUMBER(20), "OUT_LOAN_NO_BENEFICIARIES" NUMBER(20), "OUT_LOAN_BAL_OUT" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_PSA_Q_PARTA_3
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_PSA_Q_PARTA_3" ("SR_NO" NUMBER(20), "ITEMS" VARCHAR2(200), "AMT_PURCHASE_DUR_PER" NUMBER(20,2), "AMT_SOLD_DUR_PER" NUMBER(20,2), "NET_AMT" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CB_PSA_Q_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_CB_PSA_Q_SIGN" ("SR_NO" NUMBER(20), "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CEM_Q_CUNTY_EXPO_MATU
--------------------------------------------------------

  CREATE TABLE "CIMS_CEM_Q_CUNTY_EXPO_MATU" ("SR_NO" NUMBER, "COUNTRY_CODE" VARCHAR2(3), "BRANCH_CODE" VARCHAR2(20), "EXPO_CUNTY_CODE" VARCHAR2(2), "CUNTY_CLSS" VARCHAR2(200), "DUE_WTHIN_6MNHS" NUMBER(20,2), "BTN_6MNHS_TO_1YR" NUMBER(20,2), "BTN_1YR_AND_5YRS" NUMBER(20,2), "DUE_AFR_5YRS" NUMBER(20,2), "TOTAL" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CEM_Q_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CEM_Q_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CEM_Q_SIGN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CEM_Q_SIGN_INFO" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR034_TMOG_FINAL1
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR034_TMOG_FINAL1" ("CODE" NUMBER, "DURATION" VARCHAR2(100), "AMT_FINAL" NUMBER(30,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR089_FGATG_FORMIX_FINAL
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR089_FGATG_FORMIX_FINAL" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(100), "N0_OF_AC_DEMAND" NUMBER, "AMOUNT_DEMAND" NUMBER, "N0_OF_AC_SAVE" NUMBER, "AMOUNT_SAVE" NUMBER, "N0_OF_AC_TERM" NUMBER, "AMOUNT_TERM" NUMBER, "N0_OF_AC_OD" NUMBER, "AMOUNT_OD" NUMBER, "N0_OF_AC_TOTAL" NUMBER, "AMOUNT_TOTAL" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_CONS_BAL_SHEET
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_CONS_BAL_SHEET" ("DESCRIPTION" VARCHAR2(100), "VALUE" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE, "SR_NO" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_CONS_PROFIT_LOSS
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_CONS_PROFIT_LOSS" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(100), "VALUE" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_DETAILS_ON_SUBS
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_DETAILS_ON_SUBS" ("SR_N0" VARCHAR2(200), "NAME_OF_SUBS_ASSO_JV" VARCHAR2(200), "TYPE_OF_BUSN" VARCHAR2(200), "RELN_WITH_PARENT" VARCHAR2(200), "NAME_OF_REGU" VARCHAR2(200), "SHARE_HOLDING" VARCHAR2(200), "REMARKS" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_FIN_FOR_CONS_BANK
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_FIN_FOR_CONS_BANK" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE, "SR_NO" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_CPR_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_GEN_INFO" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SCH_10
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SCH_10" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SCH_11
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SCH_11" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SCH_12
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SCH_12" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SCH_13
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SCH_13" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SCH_14
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SCH_14" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SCH_15
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SCH_15" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SCH_16
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SCH_16" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SCH_1_2
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SCH_1_2" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SCH_2A
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SCH_2A" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SCH_3
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SCH_3" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SCH_4
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SCH_4" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SCH_5
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SCH_5" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SCH_6
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SCH_6" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SCH_7
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SCH_7" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SCH_8
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SCH_8" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SCH_9
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SCH_9" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SCH_I_CALLED_UNPAID
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SCH_I_CALLED_UNPAID" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(100), "NO_OF_SHARES" NUMBER(20,2), "AMT_OF_EACH_SHA" NUMBER(20,2), "TOTAL" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SCH_I_CALLED_UP
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SCH_I_CALLED_UP" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(100), "NO_OF_SHARES" NUMBER(20,2), "AMT_OF_EACH_SHA" NUMBER(20,2), "TOTAL" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SCH_I_FORFEITED
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SCH_I_FORFEITED" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(100), "NO_OF_SHARES" NUMBER(20,2), "AMT_OF_EACH_SHA" NUMBER(20,2), "TOTAL" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SCH_I_ISSUED
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SCH_I_ISSUED" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(100), "TOTAL" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE, "NO_OF_SHARES" NUMBER(20), "AMT_OF_EACH_SHA" NUMBER(20));

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SCH_I_SUBS
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SCH_I_SUBS" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(100), "NO_OF_SHARES" NUMBER(20,2), "AMT_OF_EACH_SHA" NUMBER(20,2), "TOTAL" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SEC_3_LE_LRG_EXPOS_11
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SEC_3_LE_LRG_EXPOS_11" ("SR_N0" VARCHAR2(200), "AMT_FUNDED" NUMBER(20,2), "AMT_NON_FUNDED" NUMBER(20,2), "PER_TO_CF" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SEC_3_LE_LRG_EXPOS_22
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SEC_3_LE_LRG_EXPOS_22" ("SR_N0" VARCHAR2(200), "AMT_FUNDED" NUMBER(20,2), "AMT_NON_FUNDED" NUMBER(20,2), "PER_TO_CF" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SEC_3_LE_LRG_EXPOS_3
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SEC_3_LE_LRG_EXPOS_3" ("SR_N0" VARCHAR2(200), "NAME_OF_BORR_GRP_NAME" VARCHAR2(200), "NAME_OF_GRP_COMP" VARCHAR2(200), "AMT_FUNDED" NUMBER(20,2), "AMT_NON_FUNDED" NUMBER(20,2), "PER_TO_CF" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SEC_III_LE_IND_BORR
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SEC_III_LE_IND_BORR" ("SR_N0" VARCHAR2(200), "PAN_NO" VARCHAR2(10), "BORR_NAME" VARCHAR2(200), "IND_CODE" VARCHAR2(20), "IND_NAME" VARCHAR2(200), "SECTOR" VARCHAR2(200), "AMT_FUNDED" NUMBER(20,2), "AMT_NON_FUNDED" NUMBER(20,2), "EXP_AS_PER_CF" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SEC_III_LE_LRG_EXPOS
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SEC_III_LE_LRG_EXPOS" ("SR_N0" VARCHAR2(200), "NAME_OF_BORR_GRP_NAME" VARCHAR2(200), "NAME_OF_GRP_COMP" VARCHAR2(200), "AMT_FUNDED" NUMBER(20,2), "AMT_NON_FUNDED" NUMBER(20,2), "PER_TO_CF" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SEC_IV_FOREX_EXPO
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SEC_IV_FOREX_EXPO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SEC_V
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SEC_V" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SEC_VI
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SEC_VI" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CPR_SEC_VII
--------------------------------------------------------

  CREATE TABLE "CIMS_CPR_SEC_VII" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE, "SR_NO" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_CRILC_RFA_FRAUD
--------------------------------------------------------

  CREATE TABLE "CIMS_CRILC_RFA_FRAUD" ("SR_NO" NUMBER, "TRANS_ID" VARCHAR2(100), "PAN" VARCHAR2(10), "BORR_NAME" VARCHAR2(300), "BKG_AGMNT" VARCHAR2(200), "TOTAL_AMT_OS_FND_NON_FND" NUMBER(20,2), "TOTAL_EXP_INCL_INVST" NUMBER(20,2), "RFA_FRAUD" VARCHAR2(200), "DATE_OF_FRD_RFA_CLAS" VARCHAR2(20), "STF_INVOL_YS_NO" VARCHAR2(10), "ERLY_WRNG_SNG_CLAS_LOAN" VARCHAR2(200), "WTR_COMPLAINT_FILED_WT_PLC" VARCHAR2(5), "DATE_OF_COMPLAINT" VARCHAR2(20), "WTR_FIR_FILED_YS_NO" VARCHAR2(5), "DATE_OF_FIR" VARCHAR2(20), "REMARKS_UPTO_100_CHAR" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CRILC_RFA_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_CRILC_RFA_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_CRILC_RFA_SIGNATORY
--------------------------------------------------------

  CREATE TABLE "CIMS_CRILC_RFA_SIGNATORY" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBR01_PART3_RET_ON_COMP
--------------------------------------------------------

  CREATE TABLE "CIMS_DBR01_PART3_RET_ON_COMP" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "NO_OF_COMPLAINTS_RECEVIED_X010" NUMBER, "NO_OF_COMPLAINTS_REJECTED_X020" NUMBER, "NO_OF_COMPLAINTS_REFFERED_X030" NUMBER, "REPORT_DATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_ADD_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_ADD_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_DEP_TK_T1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_DEP_TK_T1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X010" NUMBER(20,2), "REMARK_X020" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_DEP_TK_T2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_DEP_TK_T2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X030" NUMBER(20,2), "REMARK_X040" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_DEP_TK_T3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_DEP_TK_T3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X050" NUMBER(20,2), "REMARK_X060" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_HH_T1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_HH_T1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X010" NUMBER(20,2), "REMARK_X020" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_HH_T2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_HH_T2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X030" NUMBER(20,2), "REMARK_X040" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_HH_T3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_HH_T3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X050" NUMBER(20,2), "REMARK_X060" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_NFC_T1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_NFC_T1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X010" NUMBER(20,2), "REMARK_X020" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_NFC_T2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_NFC_T2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X030" NUMBER(20,2), "REMARK_X040" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_NFC_T3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_NFC_T3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X050" NUMBER(20,2), "REMARK_X060" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_OFC_IC_T1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_OFC_IC_T1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X010" NUMBER(20,2), "REMARK_X020" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_OFC_IC_T2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_OFC_IC_T2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X030" NUMBER(20,2), "REMARK_X040" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_OFC_IC_T3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_OFC_IC_T3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X050" NUMBER(20,2), "REMARK_X060" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_OFC_LIC_T1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_OFC_LIC_T1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X010" NUMBER(20,2), "REMARK_X020" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_OFC_LIC_T2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_OFC_LIC_T2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X030" NUMBER(20,2), "REMARK_X040" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_OFC_LIC_T3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_OFC_LIC_T3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X050" NUMBER(20,2), "REMARK_X060" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_OFC_MMF_T1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_OFC_MMF_T1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X010" NUMBER(20,2), "REMARK_X020" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_OFC_MMF_T2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_OFC_MMF_T2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X030" NUMBER(20,2), "REMARK_X040" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_OFC_MMF_T3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_OFC_MMF_T3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X050" NUMBER(20,4), "REMARK_X060" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_OFC_NLIC_T1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_OFC_NLIC_T1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X010" NUMBER(20,2), "REMARK_X020" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_OFC_NLIC_T2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_OFC_NLIC_T2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X030" NUMBER(20,2), "REMARK_X040" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_OFC_NLIC_T3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_OFC_NLIC_T3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X050" NUMBER(20,2), "REMARK_X060" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_OFC_PF_T1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_OFC_PF_T1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X010" NUMBER(20,2), "REMARK_X020" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_OFC_PF_T2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_OFC_PF_T2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X030" NUMBER(20,2), "REMARK_X040" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_OFC_PF_T3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_OFC_PF_T3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X050" NUMBER(20,2), "REMARK_X060" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_OFC_T1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_OFC_T1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X010" NUMBER(20,2), "REMARK_X020" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_REP
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_REP" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "CODE" VARCHAR2(100), "QTR_END_INT_OPR_X010" NUMBER(20,4), "REMARK_X020" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS01_SCOP_QUE
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS01_SCOP_QUE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS02_TABLE_1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS02_TABLE_1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "OUT_OF_DDB_X010" NUMBER(20,2), "OUT_OF_FUND_X020" NUMBER(20,2), "TOTAL_X030" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS02_TABLE_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS02_TABLE_2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "VALUE_X010" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS02_TABLE_3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS02_TABLE_3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "VALUE_X010" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS02_TABLE_3_B1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS02_TABLE_3_B1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "VALUE_X010" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS02_TABLE_3_B2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS02_TABLE_3_B2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "NOTIONAL_PRIN_AMT_X020" NUMBER(20,2), "CREDIT_EQUIVALENT_X030" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS02_TABLE_4_1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS02_TABLE_4_1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "DE_NUMBER_X010" NUMBER(20), "DE_AMOUNT_X020" NUMBER(20,2), "CE_NUMBER_X030" NUMBER(20), "CE_AMOUNT_X040" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS02_TABLE_4_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS02_TABLE_4_2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DE_NUMBER_X050" NUMBER(20), "DE_AMOUNT_X060" NUMBER(20,2), "CE_NUMBER_X070" NUMBER(20), "CE_AMOUNT_X080" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS02_TABLE_4_3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS02_TABLE_4_3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "CE_AMOUNT_X090" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS02_TABLE_5_INTERBR_1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS02_TABLE_5_INTERBR_1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "DE_NUMBER_X100" NUMBER(20), "DE_AMOUNT_X110" NUMBER(20,2), "CE_NUMBER_X120" NUMBER(20), "CE_AMOUNT_X130" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS02_TABLE_5_INTERBR_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS02_TABLE_5_INTERBR_2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DE_NUMBER_X140" NUMBER(20), "DE_AMOUNT_X150" NUMBER(20,2), "CE_NUMBER_X160" NUMBER(20), "CE_AMOUNT_X170" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS02_TABLE_5_INTERBR_3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS02_TABLE_5_INTERBR_3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "AMOUNT_X180" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS02_TABLE_6_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS02_TABLE_6_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "VAL_X010" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS03_TABLE_1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS03_TABLE_1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(1000), "VALUE_X010" NUMBER(20,2), "CUMLU_VAL_1ST_APR_2017_X010" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS03_TABLE_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS03_TABLE_2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "VALUE_X020" NUMBER(20,2), "CUMLU_VAL_1ST_APR_2017_X020" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS03_TABLE_3_AUTH_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS03_TABLE_3_AUTH_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(1000), "VALUE_X010" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS04_FILING_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS04_FILING_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "VALUE" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS04_TABLE1_PART_A
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS04_TABLE1_PART_A" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(100), "HTM_CV_X010" NUMBER(20,2), "HTM_FV_X020" NUMBER(20,2), "AFS_AC_X030" NUMBER(20,2), "AFS_CV_X040" NUMBER(20,2), "FVTPL_NH_AC_X050" NUMBER(20,2), "FVTPL_NH_CV_X060" NUMBER(20,2), "FVTPL_HFT_AC_X070" NUMBER(20,2), "FVTPL_HFT_CV_X080" NUMBER(20,2), "SAJV_CV_X090" NUMBER(20,2), "SAJV_FV_X100" NUMBER(20,2), "TOTAL_GCV_X110" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS04_TABLE2_PART_B
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS04_TABLE2_PART_B" ("SR_NO" NUMBER, "DESCRIPTION_1" VARCHAR2(1000), "DESCRIPTION_2" VARCHAR2(1000), "CODE" VARCHAR2(100), "AMT_RECLASS_QTR_X120" NUMBER(20,2), "AMT_RECLASS_YTD_X130" NUMBER(20,2), "GAINLOSS_QTR_X140" NUMBER(20,2), "GAINLOSS_YTD_X150" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS04_TABLE3_PART_B1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS04_TABLE3_PART_B1" ("SR_NO" NUMBER, "COU_BANK_NAME" VARCHAR2(1000), "COU_BANK_DOMICILE" VARCHAR2(1000), "TOTAL_EXPOSURE_X160" NUMBER(20,2), "TE_AS_PERC_OUTSIDE_X170" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS04_TABLE3_PART_B2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS04_TABLE3_PART_B2" ("SR_NO" NUMBER, "COU_BANK_NAME" VARCHAR2(1000), "CODE" VARCHAR2(100), "TOTAL_EXPOSURE_X180" NUMBER(20,2), "TE_AS_PERC_OUTSIDE_LIAB_X190" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS04_TABLE4_DETAILS_NPI
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS04_TABLE4_DETAILS_NPI" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(100), "HTM_CV_X010" NUMBER(20,2), "AFS_CV_X020" NUMBER(20,2), "FVTPL_NH_CV_X030" NUMBER(20,2), "FVTPL_HFT_CV_X040" NUMBER(20,2), "SAJV_CV_X050" NUMBER(20,2), "TOTAL_GROSS_X060" NUMBER(20,2), "NPI_PROV_X070" NUMBER(20,2), "TOTAL_NET_X080" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS04_TABLE5_FAIR_VALUE_BAL
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS04_TABLE5_FAIR_VALUE_BAL" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(100), "AFS_L1_AMT" NUMBER(20,2), "AFS_L2_AMT" NUMBER(20,2), "AFS_L3_AMT" NUMBER(20,2), "FVNH_L1_AMT" NUMBER(20,2), "FVNH_L2_AMT" NUMBER(20,2), "FVNH_L3_AMT" NUMBER(20,2), "FVHFT_L1_AMT" NUMBER(20,2), "FVHFT_L2_AMT" NUMBER(20,2), "FVHFT_L3_AMT" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS04_TABLE6_INVET_OTHER_DET
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS04_TABLE6_INVET_OTHER_DET" ("SR_NO" NUMBER, "DESCRIPTION_" VARCHAR2(100), "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(100), "AMOUNT" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS04_TABLE7_PART_E2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS04_TABLE7_PART_E2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(100), "CURRENT_YEAR_X020" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS04_TABLE8_PART_E3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS04_TABLE8_PART_E3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(100), "LEVEL1_X030" NUMBER(20,2), "LEVEL2_X040" NUMBER(20,2), "LEVEL3_X050" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS04_TABLE9_INVET_OTHER_DET_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS04_TABLE9_INVET_OTHER_DET_2" ("SR_NO" NUMBER, "OTHER_DERIVATIVES" VARCHAR2(100), "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(100), "LEVEL1_X060" NUMBER(20,2), "LEVEL2_X070" NUMBER(20,2), "LEVEL3_X080" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS04_TABLE_4_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS04_TABLE_4_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(1000), "VALUE_X010" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS05_TABLE_1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS05_TABLE_1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(1000), "NUMBER_X010" NUMBER(20), "NO_RELAT_GRP_COMPNY_X020" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS05_TABLE_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS05_TABLE_2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "NO_BC_ACCESS_PNT_X030" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS05_TABLE_3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS05_TABLE_3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(1000), "AMT_DUR_PERIOD_X040" NUMBER(20,2), "CUM_AMT_DUR_PERIOD_X040" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS05_TABLE_4_A
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS05_TABLE_4_A" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(1000), "DOWM_REC_DUR_PERIOD_X050" NUMBER(20), "CUM_DOWM_REC_DUR_PERIOD_X050" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS05_TABLE_4_B
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS05_TABLE_4_B" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(1000), "DOWM_REC_DUR_PERIOD_X060" NUMBER(20), "CUM_DOWM_REC_DUR_PERIOD_X060" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS05_TABLE_5
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS05_TABLE_5" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "TYPE" VARCHAR2(1000), "NO_PENALTIES_X070" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS05_TABLE_6
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS05_TABLE_6" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(1000), "URB_CENTER_X080" NUMBER(20), "RUR_CENTER_PERIOD_X090" NUMBER(20), "TOTAL_X100" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS05_TABLE_7_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS05_TABLE_7_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(1000), "VALUE_X010" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS06_SCOP_QUE
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS06_SCOP_QUE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS06_TABLE_10_LR_CONSO
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS06_TABLE_10_LR_CONSO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "VAL_X100" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS06_TABLE_11_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS06_TABLE_11_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(1000), "VALUE_X010" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS06_TABLE_1_LR_SOLO
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS06_TABLE_1_LR_SOLO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "EXPOSURE_AMOUNT_X010" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS06_TABLE_2_LR_SOLO
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS06_TABLE_2_LR_SOLO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "NOTIONAL_PRINCIPAL_X020" NUMBER(20,2), "CCF_FACTOR_PER_X030" NUMBER(20,4), "EXPOSURE_AMOUNT_X040" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS06_TABLE_3_LR_SOLO
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS06_TABLE_3_LR_SOLO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "NOTIONAL_PRINCIPAL_X050" NUMBER(20,2), "REPLACEMENT_COST_X060" NUMBER(20,2), "POTEN_FUTURE_EXPOSURE_X070" NUMBER(20,2), "EXPOSURE_AMOUNT_X080" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS06_TABLE_4_LR_SOLO
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS06_TABLE_4_LR_SOLO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "EXPOSURE_AMOUNT_X090" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS06_TABLE_5_LR_SOLO
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS06_TABLE_5_LR_SOLO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "VAL_X100" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS06_TABLE_6_LR_CONSO
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS06_TABLE_6_LR_CONSO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "EXPOSURE_AMOUNT_X010" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS06_TABLE_7_LR_CONSO
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS06_TABLE_7_LR_CONSO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "NOTIONAL_PRINCIPAL_X020" NUMBER(20,2), "CCF_FACTOR_PER_X030" NUMBER(20,4), "EXPOSURE_AMOUNT_X040" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS06_TABLE_8_LR_CONSO
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS06_TABLE_8_LR_CONSO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "NOTIONAL_PRINCIPAL_X050" NUMBER(20,2), "REPLACEMENT_COST_X060" NUMBER(20,2), "POTEN_FUTURE_EXPOSURE_X070" NUMBER(20,2), "EXPOSURE_AMOUNT_X080" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS06_TABLE_9_LR_CONSO
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS06_TABLE_9_LR_CONSO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "EXPOSURE_AMOUNT_X090" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_AUTH_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_AUTH_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(1000), "VALUE_X010" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR7_CONSO_TABLE1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR7_CONSO_TABLE1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(100), "ASSOC_ASF_FACTORS" NUMBER(20,4), "UNWEIGHTED_AMOUNT" NUMBER(20,2), "WEIGHTED_AMOUNT" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR7_CONSO_TABLE2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR7_CONSO_TABLE2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(100), "ASSOC_RSF_FACTORS" NUMBER(20,4), "UNWEIGHTED_AMOUNT" NUMBER(20,2), "WEIGHTED_AMOUNT" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR7_CONSO_TABLE3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR7_CONSO_TABLE3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(100), "X80" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR7_STAND_TABLE1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR7_STAND_TABLE1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(100), "ASSOC_ASF_FACTORS" NUMBER(20,4), "UNWEIGHTED_AMOUNT" NUMBER(20,2), "WEIGHTED_AMOUNT" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR7_STAND_TABLE2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR7_STAND_TABLE2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(100), "ASSOC_RSF_FACTORS" NUMBER(20,4), "UNWEIGHTED_AMOUNT" NUMBER(20,2), "WEIGHTED_AMOUNT" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR7_STAND_TABLE3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR7_STAND_TABLE3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(100), "X80" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_1_TABLE_1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_1_TABLE_1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(100), "UNWEIGHTED_AMOUNT" NUMBER(20,4), "FACTOR" NUMBER(20,4), "WEIGHTED_AMOUNT" NUMBER(20,4), "CONSO_OR_STAND" VARCHAR2(100), "RDATE" DATE, "PANEL" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_1_TABLE_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_1_TABLE_2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "X130" NUMBER(20,4), "CONSO_OR_STAND" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_1_TABLE_3_DIM
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_1_TABLE_3_DIM" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "UNWEIGHTED_AMOUNT" NUMBER(20,2), "MEMO_NO" NUMBER(20,2), "CONSO_OR_STAND" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_2_TABLE_1_DOM
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_2_TABLE_1_DOM" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(100), "CODE" VARCHAR2(100), "AMOUNT_X010" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_2_TABLE_8_OVS
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_2_TABLE_8_OVS" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(100), "CODE" VARCHAR2(100), "AMOUNT_X010" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_2_T_10_OVS_A1_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_2_T_10_OVS_A1_2" ("SR_NO" NUMBER, "COUNTRY" VARCHAR2(100), "DESCRIPTION" VARCHAR2(100), "CODE" VARCHAR2(100), "AMOUNT" NUMBER(20,2), "PERCENT_TTL_BORROWINGS" NUMBER(20,4), "PERCENT_TTL_LIABILITIES" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_2_T_11_OVS_A2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_2_T_11_OVS_A2" ("SR_NO" NUMBER, "COUNTRY" VARCHAR2(100), "NAME_OF_DEPOSITOR" VARCHAR2(100), "TYPE_OF_DEPOSIT" VARCHAR2(100), "AMOUNT" NUMBER(20,2), "PERCENT_TTL_DEPOSITS" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_2_T_12_OVS_A2_T
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_2_T_12_OVS_A2_T" ("SR_NO" NUMBER, "COUNTRY" VARCHAR2(100), "PARTICULARS" VARCHAR2(100), "CODE" VARCHAR2(100), "AMOUNT" NUMBER(20,2), "PERCENT_TTL_DEPOSITS" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_2_T_13_OVS_A3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_2_T_13_OVS_A3" ("SR_NO" NUMBER, "COUNTRY" VARCHAR2(100), "DESCRIPTION" VARCHAR2(100), "CODE" VARCHAR2(100), "AMOUNT" NUMBER(20,2), "PERCENT_TTL_BORROWINGS" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_2_T_14_OVS_B1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_2_T_14_OVS_B1" ("SR_NO" NUMBER, "COUNTRY" VARCHAR2(100), "DESCRIPTION" VARCHAR2(100), "CODE" VARCHAR2(100), "AMOUNT" NUMBER(20,2), "PERCENT_TTL_LIABILITIES" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_2_T_15_OVS_B2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_2_T_15_OVS_B2" ("SR_NO" NUMBER, "COUNTRY" VARCHAR2(100), "DESCRIPTION" VARCHAR2(100), "CODE" VARCHAR2(100), "AMOUNT" NUMBER(20,2), "PERCENT_TTL_LIABILITIES" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_2_T_2_DOM_A1_1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_2_T_2_DOM_A1_1" ("SR_NO" NUMBER, "NAME_OF_COUNTERPARTY" VARCHAR2(100), "CODE" VARCHAR2(100), "AMOUNT_X020" NUMBER(20,2), "PERCENT_TTL_DEPOSITS_X030" NUMBER(20,4), "PERCENT_TTL_LIABILITIES_X040" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_2_T_3_DOM_A1_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_2_T_3_DOM_A1_2" ("SR_NO" NUMBER, "NAME_OF_COUNTERPARTY" VARCHAR2(100), "CODE" VARCHAR2(100), "AMOUNT_X080" NUMBER(20,2), "PERCENT_TTL_BORROWINGS_X090" NUMBER(20,4), "PERCENT_TTL_LIABILITIES_X100" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_2_T_4_DOM_A2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_2_T_4_DOM_A2" ("SR_NO" NUMBER, "NAME_OF_DEPOSITOR" VARCHAR2(100), "TYPE_OF_DEPOSIT" VARCHAR2(100), "CODE" VARCHAR2(100), "AMOUNT_X140" NUMBER(20,2), "PERCENT_TTL_DEPOSITS_X150" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_2_T_5_DOM_A3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_2_T_5_DOM_A3" ("SR_NO" NUMBER, "NAME_OF_COUNTERPARTY" VARCHAR2(100), "CODE" VARCHAR2(100), "AMOUNT_X180" NUMBER(20,2), "PERCENT_TTL_BORROWINGS_X190" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_2_T_6_DOM_B1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_2_T_6_DOM_B1" ("SR_NO" NUMBER, "NAME_OF_INSTRUMENT" VARCHAR2(100), "CODE" VARCHAR2(100), "AMOUNT_X220" NUMBER(20,2), "PERCENT_TTL_LIABILITIES_X230" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_2_T_7_DOM_B2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_2_T_7_DOM_B2" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(100), "CODE" VARCHAR2(100), "AMOUNT_X260" NUMBER(20,2), "PERCENT_TTL_LIABILITIES_X270" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_2_T_9_OVS_A1_1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_2_T_9_OVS_A1_1" ("SR_NO" NUMBER, "COUNTRY" VARCHAR2(100), "DESCRIPTION" VARCHAR2(100), "CODE" VARCHAR2(100), "AMOUNT" NUMBER(20,2), "PERCENT_TTL_DEPOSITS" NUMBER(20,4), "PERCENT_TTL_LIABILITIES" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_3_TABLE_1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_3_TABLE_1" ("SR_NO" NUMBER, "TYPE_OF_ASSET" VARCHAR2(200), "LOCATION" VARCHAR2(200), "VALUE" NUMBER(20,2), "ESTIMATED_HAIRCUT_REQUIRED" NUMBER(20,4), "EXP_MONETISED_VAL_COLLA" NUMBER(20,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_3_TABLE_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_3_TABLE_2" ("SR_NO" NUMBER, "CURRENCY" VARCHAR2(100), "TYPE_OF_ASSET" VARCHAR2(200), "LOCATION" VARCHAR2(200), "VALUE" NUMBER(20,2), "ESTIMATED_HAIRCUT_REQUIRED" NUMBER(20,4), "EXP_MONETISED_VAL_COLLA" NUMBER(20,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_4_TABLE_1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_4_TABLE_1" ("SR_NO" NUMBER, "CURRENCY" VARCHAR2(100), "DETAILS_OF_HQLAS" VARCHAR2(200), "UNWEIGHTED" NUMBER(20,2), "WEIGHTED" NUMBER(20,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_4_TABLE_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_4_TABLE_2" ("SR_NO" NUMBER, "CURRENCY" VARCHAR2(100), "NET_CASH_OUTFLOWS" VARCHAR2(200), "WEIGHTED" NUMBER(20,4), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_4_TABLE_3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_4_TABLE_3" ("SR_NO" NUMBER, "CURRENCY" VARCHAR2(100), "PARTICULARS" VARCHAR2(200), "RATIO" NUMBER(20,4), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_5_T_1_PART_1A
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_5_T_1_PART_1A" ("SR_NO" NUMBER, "ENTITY" VARCHAR2(100), "FACE_VAL_X010" NUMBER(20,2), "OPENING_PRICE_X020" NUMBER(20,2), "HIGHEST_PRICE_DATE_X030" VARCHAR2(100), "HIGHEST_PRICE_AMT_X040" NUMBER(20,2), "LOWEST_PRICE_DATE_X050" VARCHAR2(100), "LOWEST_PRICE_AMT_X060" NUMBER(20,2), "CLOSING_PRICE_X070" NUMBER(20,2), "VOLATILITY_X080" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_5_T_2_PART_1B
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_5_T_2_PART_1B" ("SR_NO" NUMBER, "TYPE_OF_INSTRUMENT" VARCHAR2(100), "FACE_VAL" NUMBER(20,2), "DATE_OF_ISSUE" VARCHAR2(100), "DATE_OF_MATURITY" VARCHAR2(100), "COUPON_DIS_AT_TIME_ISSUE" NUMBER(20,2), "AMT_OUTSTAND_X090" NUMBER(20,2), "OPEN_PRICE_MONTH_X100" NUMBER(20,2), "HIGH_PRICE_MONTH_X110" NUMBER(20,2), "LOW_PRICE_MONTH_X120" NUMBER(20,2), "CLOSE_PRICE_MONTH_X130" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_5_T_3_PART_2A
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_5_T_3_PART_2A" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(100), "DATE_OF_BREACH" VARCHAR2(100), "AMOUNT_OF_BREACH_X140" NUMBER(20,2), "AMOUNT_OF_PENALTY_X150" NUMBER(20,2), "ACTION_INITIATED_X160" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_5_T_4_PART_2B
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_5_T_4_PART_2B" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(100), "NAME_OF_THE_BRANCH" VARCHAR2(100), "JURISDICTION" VARCHAR2(100), "CURRENCY" VARCHAR2(100), "DATE_OF_BREACH" VARCHAR2(100), "AMOUNT_OF_BREACH_X170" NUMBER(20,2), "AMOUNT_OF_PENALTY_X180" NUMBER(20,2), "ACTION_INITIATED_X190" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_5_T_5_PART_2C
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_5_T_5_PART_2C" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(100), "TEXT_X200" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_6_TABLE_1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_6_TABLE_1" ("SR_NO" NUMBER, "CONSO_OR_STAND" VARCHAR2(100), "PARTICULARS" VARCHAR2(100), "CODE" VARCHAR2(100), "NUMBER_X010" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_6_TABLE_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_6_TABLE_2" ("SR_NO" NUMBER, "CONSO_OR_STAND" VARCHAR2(100), "CURRENCY" VARCHAR2(100), "TRAN_MODE" VARCHAR2(100), "BANK_NAME" VARCHAR2(100), "CODE" VARCHAR2(100), "REPORT_CURRENCY_X020" VARCHAR2(100), "LVPS_NAME_XO3O" VARCHAR2(100), "PARTICIPANT_IN_LVPS_XO4O" VARCHAR2(100), "USE_CORRESP_BANKS_X050" VARCHAR2(100), "PARTICIPANT_CORRESP_BANK_X060" VARCHAR2(100), "NAME_OF_CORRESP_BANK_X070" VARCHAR2(100), "CORRESP_BANKING_SERVICES_X080" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_6_TABLE_3_SC_1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_6_TABLE_3_SC_1" ("SR_NO" NUMBER, "CONSO_OR_STAND" VARCHAR2(100), "CURRENCY" VARCHAR2(100), "TRAN_MODE" VARCHAR2(100), "BANK_NAME" VARCHAR2(100), "PARTICULARS" VARCHAR2(100), "CODE" VARCHAR2(100), "MAX_MONTH_X090" VARCHAR2(100), "SECOND_MAX_MONTH_X100" VARCHAR2(100), "THIRD_MAX_MONTH_X110" VARCHAR2(100), "AVG_MONTH_X120" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_6_TABLE_4_SC_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_6_TABLE_4_SC_2" ("SR_NO" NUMBER, "CONSO_OR_STAND" VARCHAR2(100), "CURRENCY" VARCHAR2(100), "TRAN_MODE" VARCHAR2(100), "BANK_NAME" VARCHAR2(100), "PARTICULARS" VARCHAR2(100), "CODE" VARCHAR2(100), "MIN_MONTH_X130" VARCHAR2(100), "SECOND_MIN_MONTH_X140" VARCHAR2(100), "THIRD_MIN_MONTH_X150" VARCHAR2(100), "AVG_MONTH_X160" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_6_TABLE_5_SC_3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_6_TABLE_5_SC_3" ("SR_NO" NUMBER, "CONSO_OR_STAND" VARCHAR2(100), "CURRENCY" VARCHAR2(100), "TRAN_MODE" VARCHAR2(100), "BANK_NAME" VARCHAR2(100), "PARTICULARS" VARCHAR2(100), "MIN_MONTH_X170" NUMBER(20,2), "SECOND_MIN_MONTH_X180" NUMBER(20,2), "THIRD_MIN_MONTH_X190" NUMBER(20,2), "AVG_MONTH_X200" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_6_TABLE_6_SC_4
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_6_TABLE_6_SC_4" ("SR_NO" NUMBER, "CONSO_OR_STAND" VARCHAR2(100), "CURRENCY" VARCHAR2(100), "TRAN_MODE" VARCHAR2(100), "BANK_NAME" VARCHAR2(100), "PARTICULARS" VARCHAR2(100), "CODE" VARCHAR2(100), "MAX_MONTH_X210" VARCHAR2(100), "SECOND_MAX_MONTH_X220" VARCHAR2(100), "THIRD_MAX_MONTH_X230" VARCHAR2(100), "AVG_MONTH_X240" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_6_TABLE_7_SC_5
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_6_TABLE_7_SC_5" ("SR_NO" NUMBER, "CONSO_OR_STAND" VARCHAR2(100), "CURRENCY" VARCHAR2(100), "TRAN_MODE" VARCHAR2(100), "BANK_NAME" VARCHAR2(100), "PARTICULARS" VARCHAR2(100), "CODE" VARCHAR2(100), "MAX_MONTH_X250" VARCHAR2(100), "SECOND_MAX_MONTH_X260" VARCHAR2(100), "THIRD_MAX_MONTH_X270" VARCHAR2(100), "AVG_MONTH_X280" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_6_TABLE_8_SC_6
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_6_TABLE_8_SC_6" ("SR_NO" NUMBER, "CONSO_OR_STAND" VARCHAR2(100), "CURRENCY" VARCHAR2(100), "TRAN_MODE" VARCHAR2(100), "PARTICULARS" VARCHAR2(100), "CODE" VARCHAR2(100), "D_AVG_CUM_PAY_MADE_X290" NUMBER(20,2), "CUM_PERCENT_PAY_MADE_X300" NUMBER(20,4), "D_AVG_CUM_PAY_RECEIVED_X310" NUMBER(20,2), "CUM_PERCENT_PAY_RECEIVED_X320" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_BLR_6_TABLE_9_SC_7
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_BLR_6_TABLE_9_SC_7" ("SR_NO" NUMBER, "CONSO_OR_STAND" VARCHAR2(100), "CURRENCY" VARCHAR2(100), "TRAN_MODE" VARCHAR2(100), "PARTICULARS" VARCHAR2(100), "CODE" VARCHAR2(100), "MAX_MONTH_X330" VARCHAR2(100), "SECOND_MAX_MONTH_X340" VARCHAR2(100), "THIRD_MAX_MONTH_X350" VARCHAR2(100), "AVG_MONTH_X360" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS07_SCOP_QUE
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS07_SCOP_QUE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS09_AUTH_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS09_AUTH_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(1000), "VALUE_X010" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS09_TABLE_1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS09_TABLE_1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(1000), "OS_AMT_X010" NUMBER(20,2), "NPA_OUTOF_OS_AMT_X020" NUMBER(20,2), "LOAN_PROVISION_X030" NUMBER(20,2), "OTHER_NETTING_X040" NUMBER(20,2), "NET_NPAS_X050" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS09_TABLE_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS09_TABLE_2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(1000), "TOT_BEG_PRD_X060" NUMBER(20), "OPEN_DUR_PRD_X070" NUMBER(20), "CLOSE_DUR_PRD_X080" NUMBER(20), "TOT_END_PRD_X090" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS09_TABLE_3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS09_TABLE_3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(1000), "NUMBER_AMT" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_AUTHORISED_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_AUTHORISED_SIGN" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(200), "VALUE_X010" VARCHAR2(200), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_ADDINFO
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_ADDINFO" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(200), "DETAILS_X010" VARCHAR2(200), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_III_1A
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_III_1A" ("SR_NO" NUMBER, "NAME_SFI" VARCHAR2(200), "NAME_COUNTERPARTY" VARCHAR2(200), "LOANS_AMT_X010" NUMBER(20,2), "LOANS_REPAID_X020" NUMBER(20,2), "DEP_AMT_X030" NUMBER(20,2), "DEP_WITHDRAWN_X040" NUMBER(20,2), "SHORTTERM_AMT_X050" NUMBER(20,2), "SHORTTERM_REPAID_X060" NUMBER(20,2), "EQUT_AMT_X070" NUMBER(20,2), "EQUT_REDEMP_X080" NUMBER(20,2), "NONEQUT_BONDS_AMT_X090" NUMBER(20,2), "NONEQUT_BONDS_REDEMP_X100" NUMBER(20,2), "NONEQUT_CP_AMT_X110" NUMBER(20,2), "NONEQUT_CP_REDEMP_X120" NUMBER(20,2), "NONEQUT_CD_AMT_X130" NUMBER(20,2), "NONEQUT_CD_REDEMP_X140" NUMBER(20,2), "NONEQUT_TIER_II_AMT_X150" NUMBER(20,2), "NONEQUT_TIER_II_REDEMP_X160" NUMBER(20,2), "NONEQUT_MF_AMT_X170" NUMBER(20,2), "NONEQUT_MF_REDEMP_X180" NUMBER(20,2), "NONEQUT_VENTURE_AMT_X190" NUMBER(20,2), "NON_EQUT_VENTURE_REDEMP_X200" NUMBER(20,2), "NONEQUT_PTC_AMT_X210" NUMBER(20,2), "NONEQUT_PTC_REDEMP_X220" NUMBER(20,2), "NONEQUT_ASSET_AMT_X230" NUMBER(20,2), "NONEQUT_ASSET_REDEMP_X240" NUMBER(20,2), "NONEQUT_OTHER_AMT_X250" NUMBER(20,2), "NONEQUT_OTHER_REDEMP_X260" NUMBER(20,2), "NONEQUT_TTL_AMT_X270" NUMBER(20,2), "NONEQUT_TTL_REDEMP_X280" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_III_1B
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_III_1B" ("SR_NO" NUMBER, "TRANSAC_NO" NUMBER, "NAME_SFI" VARCHAR2(200), "NAME_COUNTERPARTY" VARCHAR2(200), "NATURE_TRANSAC" VARCHAR2(200), "ORIGINAL_ISSUER_X010" VARCHAR2(200), "BEG_DATE_TRANSAC_X020" VARCHAR2(20), "END_DATE_TRANSAC_X030" VARCHAR2(20), "TENOR_TRANSAC_X040" NUMBER, "AMT_X050" NUMBER(20,2), "PER_RET_INVST_X060" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_III_1B_II
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_III_1B_II" ("SR_NO" NUMBER, "TRANSAC_NO" NUMBER, "NAME_SFI" VARCHAR2(200), "NAME_COUNTERPARTY" VARCHAR2(200), "NATURE_TRANSAC" VARCHAR2(200), "TRANSAC_SALE" VARCHAR2(200), "ORIGINAL_ISSUER_X070" VARCHAR2(200), "BEG_DATE_TRANSAC_X080" VARCHAR2(20), "END_DATE_TRANSAC_X090" VARCHAR2(20), "TENOR_TRANSAC_X100" NUMBER, "AMOUNT_X110" NUMBER(20,2), "PER_RET_INVST_X120" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_III_1C
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_III_1C" ("SR_NO" NUMBER, "NAME_OF_SFI" VARCHAR2(200), "NAME_OF_COUNTERPARTY" VARCHAR2(200), "LOANS_EXTENDED_X010" NUMBER(20,2), "DEPOSITS_PLACED_X020" NUMBER(20,2), "SHORT_TERM_LENDING_X030" NUMBER(20,2), "EQUITY_X040" NUMBER(20,2), "BONDS_X050" NUMBER(20,2), "CP_X060" NUMBER(20,2), "CD_X070" NUMBER(20,2), "TIER_II_BONDS_X080" NUMBER(20,2), "UNITS_OF_MF_X090" NUMBER(20,2), "UNITS_OF_VENTURE_FUNDS_X100" NUMBER(20,2), "PTC_X110" NUMBER(20,2), "PURCHASE_OF_ASSETS_X120" NUMBER(20,2), "OTHERS_X130" NUMBER(20,2), "TOTAL_X140" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_III_2A
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_III_2A" ("SR_NO" NUMBER, "NAME_OF_SFI" VARCHAR2(200), "NAME_OF_COUNTERPARTY" VARCHAR2(200), "CREDIT_AMT_X010" NUMBER(20,2), "CREDIT_EXP_X020" NUMBER(20,2), "FOREX_AMT_X030" NUMBER(20,2), "FOREX_EXP_X040" NUMBER(20,2), "CURR_PURCHASED_AMT_X050" NUMBER(20,2), "CURR_PURCHASED_EXP_X060" NUMBER(20,2), "CURR_FUTURES_AMT_X070" NUMBER(20,2), "CURR_FUTURES_EXP_X080" NUMBER(20,2), "SINGLE_CURR_IRS_AMT_X090" NUMBER(20,2), "SINGLE_CURR_IRS_EXP_X100" NUMBER(20,2), "CROSS_CURR_IRS_AMT_X110" NUMBER(20,2), "CROSS_CURR_IRS_EXP_X120" NUMBER(20,2), "IR_OPTION_AMT_X130" NUMBER(20,2), "IR_OPTION_EXP_X140" NUMBER(20,2), "IR_FUTURE_AMT_X150" NUMBER(20,2), "IR_FUTURE_EXP_X160" NUMBER(20,2), "FRA_AMT_X170" NUMBER(20,2), "FRA_EXP_X180" NUMBER(20,2), "BASIS_SWAPS_AMT_X190" NUMBER(20,2), "BASIS_SWAPS_EXP_X200" NUMBER(20,2), "OTHER_AMT_X210" NUMBER(20,2), "OTHER_EXP_X220" NUMBER(20,2), "TOTAL_AMT_X230" NUMBER(20,2), "TOTAL_EXP_X240" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_III_2B
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_III_2B" ("SR_NO" NUMBER, "TRANSAC_NO" NUMBER, "NAME_SFI" VARCHAR2(200), "NAME_COUNTERPARTY" VARCHAR2(200), "NATURE_OF_TRANSAC" VARCHAR2(200), "BEG_DATE_TRANSAC_X010" VARCHAR2(20), "END_DATE_TRANSAC_X020" VARCHAR2(20), "TENOR_TRANSAC_X030" NUMBER, "AMOUNT_X040" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_III_2C
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_III_2C" ("SR_NO" NUMBER, "NAME_OF_SFI" VARCHAR2(200), "NAME_OF_COUNTERPARTY" VARCHAR2(200), "CREDIT_CONTIGENT_X010" NUMBER(20,2), "FOREX_CONTRACT_X020" NUMBER(20,2), "CURR_PURCHASED_X030" NUMBER(20,2), "CURR_FUTURES_X040" NUMBER(20,2), "SINGLE_CURR_IRS_X050" NUMBER(20,2), "CROSS_CURR_IRS_X060" NUMBER(20,2), "IR_OPTION_X070" NUMBER(20,2), "IR_FUTURE_X080" NUMBER(20,2), "FRA_X090" NUMBER(20,2), "BASIS_SWAPS_X100" NUMBER(20,2), "OTHERS_X110" NUMBER(20,2), "TOTAL_X120" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_III_2D
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_III_2D" ("SR_NO" NUMBER, "TRANSAC_SR_NO" NUMBER, "NAME_OF_SFI" VARCHAR2(200), "NAME_OF_COUNTERPARTY" VARCHAR2(200), "NATURE_OF_TRANSACTIONS" VARCHAR2(200), "TRANSACTION_BEGININGDATE_X020" VARCHAR2(20), "TRANSACTION_ENDDATE_X030" VARCHAR2(20), "TENOR_X040" NUMBER, "AMOUNT_X050" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_III_3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_III_3" ("SR_NO" NUMBER, "TRANSAC_SR_NO" NUMBER, "NAME_OF_SFI" VARCHAR2(200), "NAME_OF_COUNTERPARTY" VARCHAR2(200), "NATURE_OF_TRANSACTION_X010" VARCHAR2(200), "REVENUE_X020" NUMBER(20,2), "COMISSION_X030" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_III_4
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_III_4" ("SR_NO" NUMBER, "TRANSAC_NO" NUMBER, "NAME_SFI" VARCHAR2(200), "NAME_COUNTERPARTY" VARCHAR2(200), "BEG_DATE_TRANSAC_X010" VARCHAR2(20), "END_DATE_TRANSAC_X020" VARCHAR2(20), "AMOUNT_X030" NUMBER(20,2), "REMARK_X040" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_III_4A
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_III_4A" ("SR_NO" NUMBER, "NAME_OF_SFI" VARCHAR2(200), "NAME_OF_COUNTERPARTY" VARCHAR2(200), "FB_EXPOSURE_X010" NUMBER(20,2), "NFB_EXPOSURE_X020" NUMBER(20,2), "TOTAL_X030" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_III_4B
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_III_4B" ("SR_NO" NUMBER, "NAME_OF_SFI" VARCHAR2(200), "NAME_OF_COUNTERPARTY" VARCHAR2(200), "FB_EXPOSURE_X010" NUMBER(20,2), "NFB_EXPOSURE_X020" NUMBER(20,2), "TOTAL_X030" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_III_4C
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_III_4C" ("SR_NO" NUMBER, "NAME_OF_SFI" VARCHAR2(200), "CAPITAL_MARKET_X010" NUMBER(20,2), "MONEY_MARKET_X020" NUMBER(20,2), "DEBT_MARKET_X030" NUMBER(20,2), "DERIVATIVES_X040" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_II_1A
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_II_1A" ("SR_NO" NUMBER, "ENTITY" VARCHAR2(200), "PARTICULARS" VARCHAR2(200), "AMOUNT_X010" NUMBER(20,4), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_II_1B
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_II_1B" ("SR_NO" NUMBER, "ENTITY" VARCHAR2(200), "PARTICULARS" VARCHAR2(200), "CODE" VARCHAR2(100), "AMOUNT_X010" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_II_1C
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_II_1C" ("SR_NO" NUMBER, "ENTITY" VARCHAR2(200), "PARTICULARS" VARCHAR2(200), "CODE" VARCHAR2(20), "AMOUNT_X010" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_II_2_I
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_II_2_I" ("SR_NO" NUMBER, "NAME_OF_NSFI" VARCHAR2(200), "DATE_OF_INCORP_X010" VARCHAR2(20), "CAPITAL_AND_RESERVE_X020" NUMBER(20,2), "TTL_ASSET_X030" NUMBER(20,2), "TTL_INCOME_CORE_ACTIVITY_X040" NUMBER(20,2), "TTL_INCOME_OTHER_SOURCE_X050" NUMBER(20,2), "OPS_PROFIT_LOSS_X060" NUMBER(20,2), "NET_PROFIT_LOSS_X070" NUMBER(20,2), "ROA_X080" NUMBER(20,2), "ROE_X090" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_II_2_II
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_II_2_II" ("SR_NO" NUMBER, "NAME_OF_NFE" VARCHAR2(200), "DATE_OF_INCORP_X100" VARCHAR2(20), "CAPITAL_AND_RESERVE_X110" NUMBER(20,2), "TTL_ASSET_X120" NUMBER(20,2), "TTL_INCOME_CORE_ACTIVITY_X130" NUMBER(20,2), "TTL_INCOME_OTHER_SOURCE_X140" NUMBER(20,2), "OPS_PROFIT_LOSS_X150" NUMBER(20,2), "NET_PROFIT_LOSS_X160" NUMBER(20,2), "ROA_X170" NUMBER(20,2), "ROE_X180" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_II_3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_II_3" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(200), "PER_GCAR_X010" VARCHAR2(200), "REMARK_X020" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_II_4
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_II_4" ("SR_NO" NUMBER, "NAME_OF_SFI" VARCHAR2(200), "REVENUE_CORE_ACTIVITY_X010" NUMBER(20,2), "REVENUE_OTHER_ACTIVITY_X020" NUMBER(20,2), "TTL_INCOME_X030" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_IV_1A
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_IV_1A" ("SR_NO" NUMBER, "NAME_OF_SFI" VARCHAR2(200), "NAME_OF_DIRECTORS_X010" VARCHAR2(200), "NAME_OF_TRUSTEES_X020" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_IV_1B
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_IV_1B" ("SR_NO" NUMBER, "NAME_OF_SFI" VARCHAR2(200), "NAME_OF_COUNTERPARTY" VARCHAR2(200), "TYPE_OF_SERVICE_X030" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_IV_1C
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_IV_1C" ("SR_NO" NUMBER, "NAME_OF_SFI" VARCHAR2(200), "WETHER_EVENTS_OCCUR_X040" VARCHAR2(200), "DETAILS_FRAUD_DETECT_X050" VARCHAR2(200), "PENALTY_PASSED_REGULATORS_X060" VARCHAR2(200), "PENALTY_PASSED_COURTS_X070" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_I_1A
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_I_1A" ("SR_NO" NUMBER, "NAME_OF_SFI" VARCHAR2(200), "NATURE_OF_BUSINESS_X010" VARCHAR2(200), "NAME_OF_REGULATOR_X020" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_I_1B
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_I_1B" ("SR_NO" NUMBER, "NAME_OF_NSFI" VARCHAR2(200), "NATURE_OF_BUSINESS_X030" VARCHAR2(200), "REMARKS_X040" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_I_1C
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_I_1C" ("SR_NO" NUMBER, "NAME_OF_NFE" VARCHAR2(200), "NATURE_OF_BUSINESS_X050" VARCHAR2(200), "REMARKS_X060" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_I_2A_I
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_I_2A_I" ("SR_NO" NUMBER, "NAME_OF_SFI" VARCHAR2(200), "NAME_OF_PROMOTOR" VARCHAR2(200), "NATURE_OF_RELATIONSHIP_X010" VARCHAR2(200), "PAIDUP_CAPITAL_X020" NUMBER(20,2), "PER_SHARE_BY_PROMOTER_X030" NUMBER(20,4), "PER_SHARE_ENCUMBERED_X040" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_I_2A_II
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_I_2A_II" ("SR_NO" NUMBER, "NAME_OF_SFI" VARCHAR2(200), "NAME_OF_GROUP_ENTITY" VARCHAR2(200), "PER_SHARE_HELD_X050" NUMBER(20,4), "PER_SHARE_ENCUMBERED_X060" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_I_2A_III
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_I_2A_III" ("SR_NO" NUMBER, "NAME_OF_SFI" VARCHAR2(200), "NAME_OF_GROUP_ENTITY" VARCHAR2(200), "EXTENT_OF_LIABILITY_X070" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_I_2B_I
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_I_2B_I" ("SR_NO" NUMBER, "NAME_OF_SFI" VARCHAR2(200), "NAME_OF_PROMOTER" VARCHAR2(200), "NATURE_OF_RELATIONSHIP_X080" VARCHAR2(200), "PAIDUP_CAPITAL_X090" NUMBER(20,2), "PER_SHARE_BY_PROMOTER_X100" NUMBER(20,4), "PER_SHARE_ENCUMBURED_X110" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_I_2B_II
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_I_2B_II" ("SR_NO" NUMBER, "NAME_OF_NSFI" VARCHAR2(200), "NAME_OF_GROUP_ENTITY" VARCHAR2(200), "PER_SHARE_HELD_X120" NUMBER(20,4), "PER_SHARE_ENCUMBURED_X130" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_I_2B_III
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_I_2B_III" ("SR_NO" NUMBER, "NAME_OF_NSFI" VARCHAR2(200), "NAME_OF_GROUP_ENTITY" VARCHAR2(200), "EXTENT_OF_LIABILITY_X140" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_I_2C_I
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_I_2C_I" ("SR_NO" NUMBER, "NAME_OF_NFE" VARCHAR2(200), "NAME_OF_PROMOTER" VARCHAR2(200), "NATURE_OF_RELATIONSHIP_X150" VARCHAR2(200), "PAIDUP_CAPITAL_X160" NUMBER(20,2), "PER_SHARE_HELD_X170" NUMBER(20,4), "PER_SHARE_ENCUMBURED_X180" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_I_2C_II
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_I_2C_II" ("SR_NO" NUMBER, "NAME_OF_NFE" VARCHAR2(200), "NAME_OF_GROUP_ENTITY" VARCHAR2(200), "PER_SHARE_HELD_X190" NUMBER(20,4), "PER_SHARE_ENCUMBURED_X200" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS10_FINCON_I_2C_III
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS10_FINCON_I_2C_III" ("SR_NO" NUMBER, "NAME_OF_NFE" VARCHAR2(200), "NAME_OF_GROUP_ENTITY" VARCHAR2(200), "EXTENT_OF_LIABILITY_X210" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS11_AUTH_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS11_AUTH_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(1000), "VALUE_X010" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS11_TABLE_1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS11_TABLE_1" ("SR_NO" NUMBER, "TYPE_CUST_COMPL_SUITS" VARCHAR2(1000), "COMPL_PEND_BEG_PRD_X010" NUMBER(20), "COMPL_REC_DUR_PRD_X020" NUMBER(20), "COMPL_RESOLVED_DUR_PRD_X030" NUMBER(20), "COMPL_PEND_END_PRD_X040" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS11_TABLE_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS11_TABLE_2" ("SR_NO" NUMBER, "NATURE_CUST_COMPL" VARCHAR2(1000), "COMPL_PEND_BEG_PRD_X050" NUMBER(20), "COMPL_REC_DUR_PRD_X060" NUMBER(20), "COMPL_RESOLVED_DUR_PRD_X070" NUMBER(20), "AVG_DISPO_TIME_COMPL_X080" NUMBER(20,4), "COMPL_PEND_END_PRD_X090" NUMBER(20), "COMPENS_PAID_CUST_X100" NUMBER(20,4), "REMARKS_X110" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS11_TABLE_3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS11_TABLE_3" ("SR_NO" NUMBER, "NATURE_CUST_COMPL" VARCHAR2(1000), "CUST_COMPL_AGING" VARCHAR2(1000), "COMPL_PEND_END_PRD_X120" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS11_TABLE_4
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS11_TABLE_4" ("SR_NO" NUMBER, "CHNL_RECIEPT_COMPL" VARCHAR2(1000), "COMPL_REC_DUR_PRD_X010" NUMBER(20), "REMARKS_X020" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS11_TABLE_5
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS11_TABLE_5" ("SR_NO" NUMBER, "DISPO_COMPL" VARCHAR2(1000), "NO_COMPL_WITHIN_TAT_X030" NUMBER(20), "NO_COMPL_ABOVE_TAT_X040" NUMBER(20), "TOTAL_NO_COMPL_X040" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS11_TABLE_6
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS11_TABLE_6" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(1000), "NO_OF_AWARDS_X060" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS11_TABLE_7
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS11_TABLE_7" ("SR_NO" NUMBER, "TIME_TAKEN_ADRS_COMPL" VARCHAR2(1000), "NO_OF_COMPL_X070" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS11_TABLE_8
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS11_TABLE_8" ("SR_NO" NUMBER, "AGE_WISE_OS_COMPL" VARCHAR2(1000), "NO_OF_COMPL_X080" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS11_TABLE_9
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS11_TABLE_9" ("SR_NO" NUMBER, "ACTION_BASE_ON_COMPL" VARCHAR2(1000), "COMPL_PEND_BEG_PRD_X090" NUMBER(20), "COMPL_REC_DUR_PRD_X100" NUMBER(20), "COMPL_RESOLVED_DUR_PRD_X110" NUMBER(20), "COMPL_PEND_END_PRD_X120" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS12_Q_AUTH_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS12_Q_AUTH_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(1000), "VALUE_X010" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS12_Q_SCOP_QUE
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS12_Q_SCOP_QUE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS12_Q_SEC_A
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS12_Q_SEC_A" ("SRNO" NUMBER, "NAME_OF_ENTITY" VARCHAR2(200), "AREA_OF_OPER" VARCHAR2(100), "TYPE_OF_ENTITY_X010" VARCHAR2(500), "FINANC_CLASS_X020" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS12_Q_SEC_B
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS12_Q_SEC_B" ("SRNO" NUMBER, "NAME_OF_GROUP" VARCHAR2(200), "AREA_OF_OPER" VARCHAR2(100), "TYPE_OF_ENTITY_X010" VARCHAR2(1000), "FINANC_CLASS_X020" VARCHAR2(200), "AMT_BNK_EQU_INV_IN_COMP_X030" NUMBER(20,2), "PER_OF_BNK_HOLD_IN_EQU_X040" NUMBER(20,4), "FUND_AMT_OUT_X050" NUMBER(20,2), "FUND_CRDT_EXPO_X060" NUMBER(20,2), "NON_FUND_AMT_OUT_X070" NUMBER(20,2), "NON_FUND_EXPO_X080" NUMBER(20,2), "INVES_EXPO_X090" NUMBER(20,2), "EXEMP_EXPO_X100" NUMBER(20,2), "TTL_AMT_OUT_X110" NUMBER(20,2), "TTL_EXPO_X120" NUMBER(20,2), "ASSET_CLASSIF_X130" VARCHAR2(200), "PROVISI_HELD_X140" NUMBER(20,2), "TTL_OUT_UNSECURED_X150" NUMBER(20,2), "RESON_BRCH_PRUD_LIMT_X160" VARCHAR2(200), "DESCP_INTR_GRUP_SUPPOT_X170" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS12_Q_SEC_C
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS12_Q_SEC_C" ("SRNO" NUMBER, "NAME_OF_ASSIS_SHARE_HOLD" VARCHAR2(200), "NATURE_OF_INT_X010" VARCHAR2(1000), "TYPE_OF_EXPO_X020" VARCHAR2(1000), "AMT_OF_EXPO_X030" NUMBER(20,2), "TERMS_CREDIT_EXPO_X040" VARCHAR2(1000), "VAL_OF_SECURITIES_X050" NUMBER(20,2), "ASSET_CLASSI_X060" VARCHAR2(1000), "PROVISION_HELD_X070" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS12_Q_SEC_D_A
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS12_Q_SEC_D_A" ("SRNO" NUMBER, "NAME_OF_ASSIS_MANAGR" VARCHAR2(200), "TYPE_OF_BNK_EXPO_X010" VARCHAR2(100), "AMT_OF_BNK_EXPO_X020" NUMBER(20,2), "TERMS_OF_CREDIT_EXPO_X030" VARCHAR2(200), "VAL_OF_SECURITIES_X040" NUMBER(20,2), "ASSET_CLASSI_X050" VARCHAR2(200), "PROVISION_HELD_X060" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS12_Q_SEC_D_B
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS12_Q_SEC_D_B" ("SRNO" NUMBER, "NAME_OF_ASSIS_MANAGR" VARCHAR2(200), "NAME_OF_INTERES_DIRECTOR" VARCHAR2(100), "NATURE_OF_INT_X070" VARCHAR2(200), "TYPE_OF_BNK_EXPO_X080" VARCHAR2(200), "AMT_OF_BNK_EXPO_X090" NUMBER(20,2), "TERMS_OF_CREDIT_EXPO_X100" VARCHAR2(200), "VAL_OF_SECURITIES_X110" NUMBER(20,2), "ASSET_CLASSI_X120" VARCHAR2(200), "PROVISION_HELD_X130" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS13_AUTH_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS13_AUTH_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(1000), "VALUE_X010" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS13_SCOP_QUE
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS13_SCOP_QUE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS13_TABLE_1
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS13_TABLE_1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(1000), "VALUE" NUMBER(20,2), "RDATE" DATE, "CATEGORY" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_DBS13_TABLE_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS13_TABLE_2" ("SR_NO" NUMBER, "SINGLE_GROUP_CONNE_CP" VARCHAR2(1000), "PAN_GRPID_CP" VARCHAR2(1000), "NAME_CP" VARCHAR2(1000), "EXP_AMT_X020" NUMBER(20,2), "EXP_PERC_TEIR1_CAP_X030" NUMBER(20,4), "RDATE" DATE, "CATEGORY" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_DBS13_TABLE_3
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS13_TABLE_3" ("SR_NO" NUMBER, "SINGLE_GROUP_CONNE_CP" VARCHAR2(1000), "PAN_GRPID_CP" VARCHAR2(1000), "NAME_CP" VARCHAR2(1000), "EXP_AMT_X010" NUMBER(20,2), "EXP_PERC_TEIR1_CAP_X020" NUMBER(20,4), "RDATE" DATE, "CATEGORY" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_DBS13_TABLE_4
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS13_TABLE_4" ("SR_NO" NUMBER, "SINGLE_GROUP_CONNE_CP" VARCHAR2(1000), "PAN_GRPID_CP" VARCHAR2(1000), "NAME_CP" VARCHAR2(1000), "EXP_AMT_X010" NUMBER(20,2), "EXP_PERC_TEIR1_CAP_X020" NUMBER(20,4), "RDATE" DATE, "CATEGORY" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_DBS13_TABLE_5
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS13_TABLE_5" ("SR_NO" NUMBER, "SINGLE_GROUP_CONNE_CP" VARCHAR2(1000), "PAN_GRPID_CP" VARCHAR2(1000), "NAME_CP" VARCHAR2(1000), "EXP_AMT_X010" NUMBER(20,2), "EXP_PERC_TEIR1_CAP_X020" NUMBER(20,4), "RDATE" DATE, "CATEGORY" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_DBS16_AUTH_SIGNATORY
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS16_AUTH_SIGNATORY" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(200), "CODE" VARCHAR2(200), "VALUE_X010" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS16_DBS_STRESSED_MSME
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS16_DBS_STRESSED_MSME" ("SR_NO" NUMBER, "NAME_OF_BORROWER" VARCHAR2(200), "PAN_BORROWER" VARCHAR2(200), "ELIGIBLE_MSME_ENTITY" VARCHAR2(200), "PAN_OF_MSME" VARCHAR2(200), "LOCATION_MSME" VARCHAR2(200), "MSME_CATEGORY" VARCHAR2(200), "SECTOR" VARCHAR2(200), "MSME_AMT_CLASS_X010" VARCHAR2(200), "MSMSE_AMT_SMA2_X020" VARCHAR2(200), "NO_FRAUD_WILFUL_X030" VARCHAR2(200), "PROMOTERS_STAKE_X040" NUMBER(20,2), "EXIST_SANCTION_LOAN_X050" NUMBER(20,2), "EXIST_OUTSTAND_LOAN_X060" NUMBER(20,2), "DECLARATION_FLAG_X070" VARCHAR2(200), "DATE_SANCTION_LOAN_X080" VARCHAR2(200), "LOAN_SANCTION_X090" NUMBER(20,2), "CGTMSE_APPROVAL_X010" VARCHAR2(200), "TENOR_LOAN_X110" NUMBER(20,2), "TENURE_MORATORIUM_LOAN_X120" NUMBER(20,2), "OUTSTAND_LOAN_SANCTION_X130" NUMBER(20,2), "CLASSIFY_LOAN_X140" VARCHAR2(200), "OUTSTAND_LOAN_MSME_X150" NUMBER(20,2), "MSME_ACOUNT_X160" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DBS16_SCOP_QUE
--------------------------------------------------------

  CREATE TABLE "CIMS_DBS16_SCOP_QUE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS01_TABLE_1
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS01_TABLE_1" ("SR_NO" NUMBER, "TYPE_TRANSACTION" VARCHAR2(1000), "COMPLAINT_TYPE" VARCHAR2(1000), "COMPL_PEND_BEG_PRD_X010" NUMBER(20), "COMPL_REC_DUR_PRD_X020" NUMBER(20), "TOTAL_COMPLAINT_X030" NUMBER(20), "COMPLAINT_RESOLVED_X040" NUMBER(20), "COMPL_PEND_END_PRD_X050" NUMBER(20), "COMPENS_PAID_CUST_X060" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS01_TABLE_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS01_TABLE_2" ("SR_NO" NUMBER, "TYPE_TRANSACTION" VARCHAR2(1000), "COMPLAINT_TYPE" VARCHAR2(1000), "ATM_COMPLAINT_AGING" VARCHAR2(1000), "COMPLAINT_RESOLVED_X070" NUMBER(20), "COMPL_PENDING_X080" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS01_TABLE_3
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS01_TABLE_3" ("SR_NO" NUMBER, "BANK_WLA_CODE" VARCHAR2(1000), "CATEGORY_ATM" VARCHAR2(1000), "COMPLAINT_TYPE" VARCHAR2(1000), "BANK_WLA_NAME_X090" VARCHAR2(1000), "TOTAL_NO_PEND_COMPL_X100" NUMBER(20), "AMT_OUTSTAND_X110" NUMBER(20,2), "COMPENSATION_X120" NUMBER(20,2), "MAJOR_REASON_OTHER_X130" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS01_TABLE_4
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS01_TABLE_4" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CHARGEBACKS_X140" NUMBER(20), "REPRESENTMENT_X150" NUMBER(20), "CREDIT_ADJUST_X160" NUMBER(20), "DEBIT_ADJUST_X170" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS03_TABLE_1
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS03_TABLE_1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "TOT_NO_MOB_BANK_DURING_X010" NUMBER, "TOT_NO_MOB_BANK_END_X020" NUMBER, "TOT_NO_ACTIVE_CUST_X030" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS03_TABLE_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS03_TABLE_2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "GS_MOB_APP_VOL_X040" NUMBER, "GS_MOB_APP_VAL_X050" NUMBER(20,2), "GS_OTHER_VOL_X060" NUMBER, "GS_OTHER_VAL_X070" NUMBER(20,2), "GS_TOTAL_VOL_X080" NUMBER, "GS_TOTAL_VAL_X090" NUMBER(20,2), "FT_MOB_RTGS_VOL_X100" NUMBER, "FT_MOB_RTGS_VAL_X110" NUMBER(20,2), "FT_MOB_NEFT_VOL_X120" NUMBER, "FT_MOB_NEFT_VAL_X130" NUMBER(20,2), "FT_MOB_IMPS_VOL_X140" NUMBER, "FT_MOB_IMPS_VAL_X150" NUMBER(20,2), "FT_MOB_UPI_VOL_X160" NUMBER, "FT_MOB_UPI_VAL_X170" NUMBER(20,2), "FT_MOB_OTHER_VOL_X180" NUMBER, "FT_MOB_OTHER_VAL_X190" NUMBER(20,2), "FT_MOB_TOTAL_VOL_X200" NUMBER, "FT_MOB_TOTAL_VAL_X210" NUMBER(20,2), "FT_BUSN_RTGS_VOL_X220" NUMBER, "FT_BUSN_RTGS_VAL_X230" NUMBER(20,2), "FT_BUSN_NEFT_VOL_X240" NUMBER, "FT_BUSN_NEFT_VAL_X250" NUMBER(20,2), "FT_BUSN_IMPS_VOL_X260" NUMBER, "FT_BUSN_IMPS_VAL_X270" NUMBER(20,2), "FT_BUSN_UPI_VOL_X280" NUMBER, "FT_BUSN_UPI_VAL_X290" NUMBER(20,2), "FT_BUSN_OTHER_VOL_X300" NUMBER, "FT_BUSN_OTHER_VAL_X310" NUMBER(20,2), "FT_BUSN_TOTAL_VOL_X320" NUMBER, "FT_BUSN_TOTAL_VAL_X330" NUMBER(20,2), "FT_OTHER_VOL_X340" NUMBER, "FT_OTHER_VAL_X350" NUMBER(20,2), "FT_TOTAL_VOL_X360" NUMBER, "FT_TOTAL_VAL_X370" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS03_TABLE_3
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS03_TABLE_3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "GS_MOB_APP_VOL_X380" NUMBER, "GS_MOB_APP_VAL_X390" NUMBER(20,2), "GS_OTHER_VOL_X400" NUMBER, "GS_OTHER_VAL_X410" NUMBER(20,2), "GS_TOTAL_VOL_X420" NUMBER, "GS_TOTAL_VAL_X430" NUMBER(20,2), "FT_MOB_VOL_X440" NUMBER, "FT_MOB_VAL_X450" NUMBER(20,2), "FT_BUSN_VOL_X460" NUMBER, "FT_BUSN_VAL_X470" NUMBER(20,2), "FT_OTHER_VOL_X480" NUMBER, "FT_OTHER_VAL_X490" NUMBER(20,2), "FT_TOTAL_VOL_X500" NUMBER, "FT_TOTAL_VAL_X510" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS04_TABLE_1
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS04_TABLE_1" ("SR_NO" NUMBER, "DESTI_STATE" VARCHAR2(1000), "DESTI_REGION" VARCHAR2(1000), "NO_OF_AGENTS_X010" NUMBER(20), "NO_OF_SUBAGENTSX020" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS04_TABLE_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS04_TABLE_2" ("SR_NO" NUMBER, "REMIT_COUNTRY" VARCHAR2(1000), "DESTI_STATE" VARCHAR2(1000), "DESTI_REGION" VARCHAR2(1000), "REMIT_VAL_BAND" VARCHAR2(1000), "TYPE_TRANS" VARCHAR2(1000), "NO_OF_TRANS_X030" NUMBER(20), "VAL_TRANS_USD_X040" NUMBER(20,2), "VAL_TRANS_INR_X050" NUMBER(20,2), "CHARGES_COLLECTED_X060" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS05_SCOP_QUE
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS05_SCOP_QUE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS05_TABLE_1
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS05_TABLE_1" ("SR_NO" NUMBER, "TYPE_PPI_ISSUED" VARCHAR2(1000), "COMPLAINT_TYPE" VARCHAR2(1000), "COMPL_PEND_BEG_PRD_X010" NUMBER(20), "COMPL_REC_DUR_PRD_X020" NUMBER(20), "TOTAL_COMPLAINT_X030" NUMBER(20), "COMPLAINT_RESOLVED_X040" NUMBER(20), "COMPL_PEND_END_PRD_X050" NUMBER(20), "REMARKS_X060" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS05_TABLE_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS05_TABLE_2" ("SR_NO" NUMBER, "TYPE_PPI_ISSUED" VARCHAR2(1000), "COMPLAINT_TYPE" VARCHAR2(1000), "TIME_TAKEN_RESOLVE_COMPL" VARCHAR2(1000), "COMPLAINT_RESOLVE_X050" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS06_SCOP_QUE
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS06_SCOP_QUE" ("SR_NO" VARCHAR2(20), "PARTICULARS" VARCHAR2(100), "DETAILS_X010" VARCHAR2(100), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_DPSS06_TABLE1
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS06_TABLE1" ("SR_NO" NUMBER(20), "DESCRIPTION" VARCHAR2(200), "CB_PPI_NUM_X010" NUMBER(20), "CB_PPI_AMT_X020" NUMBER(20,2), "OUT_BAL_ESCROW_X030" NUMBER(20,2), "TOT_NUM_FRESH_PPIS_X040" NUMBER(20), "NUM_PPI_CON_X050" NUMBER(20), "BAL_PPI_CON_X060" NUMBER(20,2), "NUM_PPI_CON_OTH_X070" NUMBER(20), "BAL_PPI_CON_OTH_X080" NUMBER(20,2), "DB_CD_TOT_NUM_TRN_X090" NUMBER(20), "DB_CD_TOT_AMT_TRN_X100" NUMBER(20,2), "CASH_TOT_NUM_TRN_X110" NUMBER(20), "CASH_TOT_AMT_TRN_X120" NUMBER(20,2), "MTSS_TOT_NUM_TRN_X130" NUMBER(20), "MTSS_TOT_AMT_TRN_X140" NUMBER(20,2), "PPI_TOT_NUM_TRN_X150" NUMBER(20), "PPI_TOT_AMT_TRN_X160" NUMBER(20,2), "OTH_PPI_TOT_NUM_TRN_X170" NUMBER(20), "OTH_PPI_TOT_NUM_TRN_X180" NUMBER(20,2), "REFUND_AGNST_SUCCES_TRN_X190" NUMBER(20,2), "CASHBACKS_LOADED_X200" NUMBER(20,2), "POS_NUM_P2M_TRN_X210" NUMBER(20), "POS_AMT_P2M_TRN_X220" NUMBER(20,2), "ONLINE_NUM_P2M_TRN_X230" NUMBER(20), "ONLINE_AMT_P2M_TRN_X240" NUMBER(20,2), "TOT_NUM_MERCHANT_ACQD_X250" NUMBER(20), "TOTAL_NO_P2P_TRN_X260" NUMBER(20), "TOTAL_AMT_P2P_TRN_X270" NUMBER(20,2), "NO_P2P_TRN_ISS_OTH_PPI_X280" NUMBER(20), "AMT_P2P_TRN_ISS_OTH_PPI_X290" NUMBER(20,2), "TOTAL_NO_PPI_P2B_X300" NUMBER(20), "TOTAL_AMT_PPI_P2B_X310" NUMBER(20,2), "TOT_AMT_COMM_CHARG_X320" NUMBER(20,2), "ATM_NO_CASH_WITHDRW_X330" NUMBER(20), "ATM_AMT_CASH_WITHDRW_X340" NUMBER(20,2), "POS_NO_CASH_WITHDRW_X350" NUMBER(20), "POS_AMT_CASH_WITHDRW_X360" NUMBER(20,2), "AGNT_BC_NO_CASH_WITHDRW_X370" NUMBER(20), "AGNT_BC_AMT_CASH_WITHDRW_X380" NUMBER(20,2), "TOT_NO_CBOT_X390" NUMBER(20), "TOT_AMT_CBOT_X400" NUMBER(20,2), "TOT_NO_PPI_CLOSED_X410" NUMBER(20), "TOT_AMT_PPI_CLOSED_X420" NUMBER(20,2), "TOT_UNSPENT_BAL_PPI_X430" NUMBER(20,2), "TOT_NO_EXP_PPI_X440" NUMBER(20), "TOT_AMT_EXP_PPI_X450" NUMBER(20,2), "TOT_OUT_PPI_X460" NUMBER(20,2), "FORFEITURE_NO_EXP_PPI__X470" NUMBER(20), "FORFEITURE_AMT_EXP_PPI_X480" NUMBER(20,2), "NO_ACTIVE_PPI_X490" NUMBER(20), "AMT_ACTIVE_PPI_X500" NUMBER(20,2), "NO_INACTIVE_PPI_X510" NUMBER(20), "AMT_INACTIVE_PPI_X520" NUMBER(20,2), "AMT_INACTIVE_PPI_NO_BAL_X530" NUMBER(20,2), "CB_NO_OUT_PPI_X540" NUMBER(20), "CB_AMT_OUT_PPI_X550" NUMBER(20,2), "OUT_LIAB_TWRD_MARCHANT_X560" NUMBER(20,2), "OUT_BAL_ESCROW_ACC_X570" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS06_TABLE2
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS06_TABLE2" ("SR_NO" NUMBER(20), "DESCRIPTION" VARCHAR2(200), "CB_PPI_NUM_X570" NUMBER(20), "CB_PPI_AMT_X580" NUMBER(20,2), "OUT_BAL_ESCROW_X590" NUMBER(20,2), "TOT_NUM_FRESH_PPIS_X600" NUMBER(20), "NUM_PPI_CON_X610" NUMBER(20), "BAL_PPI_CON_X620" NUMBER(20,2), "NUM_PPI_CON_OTH_X630" NUMBER(20), "BAL_PPI_CON_OTH_X640" NUMBER(20,2), "DB_CD_TOT_NUM_TRN_X650" NUMBER(20), "DB_CD_TOT_AMT_TRN_X660" NUMBER(20,2), "CASH_TOT_NUM_TRN_X670" NUMBER(20), "CASH_TOT_AMT_TRN_X680" NUMBER(20,2), "MTSS_TOT_NUM_TRN_X690" NUMBER(20), "MTSS_TOT_AMT_TRN_X700" NUMBER(20,2), "PPI_TOT_NUM_TRN_X710" NUMBER(20), "PPI_TOT_AMT_TRN_X720" NUMBER(20,2), "OTH_PPI_TOT_NUM_TRN_X730" NUMBER(20), "OTH_PPI_TOT_NUM_TRN_X740" NUMBER(20,2), "REFUND_AGNST_SUCCES_TRN_X750" NUMBER(20,2), "CASHBACKS_LOADED_X760" NUMBER(20,2), "POS_NUM_P2M_TRN_X770" NUMBER(20), "POS_AMT_P2M_TRN_X780" NUMBER(20,2), "ONLINE_NUM_P2M_TRN_X790" NUMBER(20), "ONLINE_AMT_P2M_TRN_X800" NUMBER(20,2), "TOT_NUM_MERCHANT_ACQD_X810" NUMBER(20), "TOTAL_NO_P2P_TRN_X820" NUMBER(20), "TOTAL_AMT_P2P_TRN_X830" NUMBER(20,2), "NO_P2P_TRN_ISS_OTH_PPI_X840" NUMBER(20), "AMT_P2P_TRN_ISS_OTH_PPI_X850" NUMBER(20,2), "TOTAL_NO_PPI_P2B_X860" NUMBER(20), "TOTAL_AMT_PPI_P2B_X870" NUMBER(20,2), "TOT_AMT_COMM_CHARG_X880" NUMBER(20,2), "ATM_NO_CASH_WITHDRW_X890" NUMBER(20), "ATM_AMT_CASH_WITHDRW_X900" NUMBER(20,2), "POS_NO_CASH_WITHDRW_X910" NUMBER(20), "POS_AMT_CASH_WITHDRW_X920" NUMBER(20,2), "AGNT_BC_NO_CASH_WITHDRW_X930" NUMBER(20), "AGNT_BC_AMT_CASH_WITHDRW_X940" NUMBER(20,2), "TOT_NO_CBOT_X950" NUMBER(20), "TOT_AMT_CBOT_X960" NUMBER(20,2), "TOT_NO_PPI_CLOSED_X970" NUMBER(20), "TOT_AMT_PPI_CLOSED_X980" NUMBER(20,2), "TOT_UNSPENT_BAL_PPI_X990" NUMBER(20,2), "TOT_NO_EXP_PPI_X1000" NUMBER(20), "TOT_AMT_EXP_PPI_X1010" NUMBER(20,2), "TOT_OUT_PPI_X1020" NUMBER(20,2), "FORFEITURE_NO_EXP_PPI__X1030" NUMBER(20), "FORFEITURE_AMT_EXP_PPI_X1040" NUMBER(20,2), "NO_ACTIVE_PPI_X1050" NUMBER(20), "AMT_ACTIVE_PPI_X1060" NUMBER(20,2), "NO_INACTIVE_PPI_X1070" NUMBER(20), "AMT_INACTIVE_PPI_X1080" NUMBER(20,2), "AMT_INACTIVE_PPI_NO_BAL_X1090" NUMBER(20,2), "CB_NO_OUT_PPI_X1100" NUMBER(20), "CB_AMT_OUT_PPI_X1110" NUMBER(20,2), "OUT_LIAB_TWRD_MARCHANT_X1120" NUMBER(20,2), "OUT_BAL_ESCROW_ACC_X1130" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS06_TABLE3
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS06_TABLE3" ("SR_NO" NUMBER(20), "DESCRIPTION" VARCHAR2(200), "CB_PPI_NUM_X1140" NUMBER(20), "CB_PPI_AMT_X1150" NUMBER(20,2), "OUT_BAL_ESCROW_X1160" NUMBER(20,2), "TOT_NUM_FRESH_PPIS_X1170" NUMBER(20), "NUM_PPI_CON_X1180" NUMBER(20), "BAL_PPI_CON_X1190" NUMBER(20,2), "NUM_PPI_CON_OTH_X1200" NUMBER(20), "BAL_PPI_CON_OTH_X1210" NUMBER(20,2), "DB_CD_TOT_NUM_TRN_X1220" NUMBER(20), "DB_CD_TOT_AMT_TRN_X1230" NUMBER(20,2), "CASH_TOT_NUM_TRN_X1240" NUMBER(20), "CASH_TOT_AMT_TRN_X1250" NUMBER(20,2), "MTSS_TOT_NUM_TRN_X1260" NUMBER(20), "MTSS_TOT_AMT_TRN_X1270" NUMBER(20,2), "PPI_TOT_NUM_TRN_X1280" NUMBER(20), "PPI_TOT_AMT_TRN_X1290" NUMBER(20,2), "OTH_PPI_TOT_NUM_TRN_X1300" NUMBER(20), "OTH_PPI_TOT_NUM_TRN_X1310" NUMBER(20,2), "REFUND_AGNST_SUCCES_TRN_X1320" NUMBER(20,2), "CASHBACKS_LOADED_X1330" NUMBER(20,2), "POS_NUM_P2M_TRN_X1340" NUMBER(20), "POS_AMT_P2M_TRN_X1350" NUMBER(20,2), "ONLINE_NUM_P2M_TRN_X1360" NUMBER(20), "ONLINE_AMT_P2M_TRN_X1370" NUMBER(20,2), "TOT_NUM_MERCHANT_ACQD_X1380" NUMBER(20), "TOTAL_NO_P2P_TRN_X1390" NUMBER(20), "TOTAL_AMT_P2P_TRN_X1400" NUMBER(20,2), "NO_P2P_TRN_ISS_OTH_PPI_X1410" NUMBER(20), "AMT_P2P_TRN_ISS_OTH_PPI_X1420" NUMBER(20,2), "TOTAL_NO_PPI_P2B_X1430" NUMBER(20), "TOTAL_AMT_PPI_P2B_X1440" NUMBER(20,2), "TOT_AMT_COMM_CHARG_X1450" NUMBER(20,2), "ATM_NO_CASH_WITHDRW_X1460" NUMBER(20), "ATM_AMT_CASH_WITHDRW_X1470" NUMBER(20,2), "POS_NO_CASH_WITHDRW_X1480" NUMBER(20), "POS_AMT_CASH_WITHDRW_X1490" NUMBER(20,2), "AGNT_BC_NO_CASH_WITHDRW_X1500" NUMBER(20), "AGNT_BC_AMT_CASH_WITHDRW_X1510" NUMBER(20,2), "TOT_NO_CBOT_X1520" NUMBER(20), "TOT_AMT_CBOT_X1530" NUMBER(20,2), "TOT_NO_PPI_CLOSED_X1540" NUMBER(20), "TOT_AMT_PPI_CLOSED_X1550" NUMBER(20,2), "TOT_UNSPENT_BAL_PPI_X1560" NUMBER(20,2), "TOT_NO_EXP_PPI_X1570" NUMBER(20), "TOT_AMT_EXP_PPI_X1580" NUMBER(20,2), "TOT_OUT_PPI_X1590" NUMBER(20,2), "FORFEITURE_NO_EXP_PPI__X1600" NUMBER(20), "FORFEITURE_AMT_EXP_PPI_X1610" NUMBER(20,2), "NO_ACTIVE_PPI_X1620" NUMBER(20), "AMT_ACTIVE_PPI_X1630" NUMBER(20,2), "NO_INACTIVE_PPI_X1640" NUMBER(20), "AMT_INACTIVE_PPI_X1650" NUMBER(20,2), "AMT_INACTIVE_PPI_NO_BAL_X1660" NUMBER(20,2), "CB_NO_OUT_PPI_X1670" NUMBER(20), "CB_AMT_OUT_PPI_X1680" NUMBER(20,2), "OUT_LIAB_TWRD_MARCHANT_X1690" NUMBER(20,2), "OUT_BAL_ESCROW_ACC_X1700" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS06_TABLE4
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS06_TABLE4" ("SR_NO" NUMBER(20), "DESCRIPTION" VARCHAR2(200), "CB_PPI_NUM_X1710" NUMBER(20), "CB_PPI_AMT_X1720" NUMBER(20,2), "OUT_BAL_ESCROW_X1730" NUMBER(20,2), "TOT_NUM_FRESH_PPIS_X1740" NUMBER(20), "NUM_PPI_CON_X1750" NUMBER(20), "BAL_PPI_CON_X1760" NUMBER(20,2), "NUM_PPI_CON_OTH_X1770" NUMBER(20), "BAL_PPI_CON_OTH_X1780" NUMBER(20,2), "DB_CD_TOT_NUM_TRN_X1790" NUMBER(20), "DB_CD_TOT_AMT_TRN_X1800" NUMBER(20,2), "CASH_TOT_NUM_TRN_X1810" NUMBER(20), "CASH_TOT_AMT_TRN_X1820" NUMBER(20,2), "MTSS_TOT_NUM_TRN_X1830" NUMBER(20), "MTSS_TOT_AMT_TRN_X1840" NUMBER(20,2), "PPI_TOT_NUM_TRN_X1850" NUMBER(20), "PPI_TOT_AMT_TRN_X1860" NUMBER(20,2), "OTH_PPI_TOT_NUM_TRN_X1870" NUMBER(20), "OTH_PPI_TOT_NUM_TRN_X1880" NUMBER(20,2), "REFUND_AGNST_SUCCES_TRN_X1890" NUMBER(20,2), "CASHBACKS_LOADED_X1900" NUMBER(20,2), "POS_NUM_P2M_TRN_X1910" NUMBER(20), "POS_AMT_P2M_TRN_X1920" NUMBER(20,2), "ONLINE_NUM_P2M_TRN_X1930" NUMBER(20), "ONLINE_AMT_P2M_TRN_X1940" NUMBER(20,2), "TOT_NUM_MERCHANT_ACQD_X1950" NUMBER(20), "TOTAL_NO_P2P_TRN_X1960" NUMBER(20), "TOTAL_AMT_P2P_TRN_X1970" NUMBER(20,2), "NO_P2P_TRN_ISS_OTH_PPI_X1980" NUMBER(20), "AMT_P2P_TRN_ISS_OTH_PPI_X1990" NUMBER(20,2), "TOTAL_NO_PPI_P2B_X2000" NUMBER(20), "TOTAL_AMT_PPI_P2B_X2010" NUMBER(20,2), "TOT_AMT_COMM_CHARG_X2020" NUMBER(20,2), "ATM_NO_CASH_WITHDRW_X2030" NUMBER(20), "ATM_AMT_CASH_WITHDRW_X2040" NUMBER(20,2), "POS_NO_CASH_WITHDRW_X2050" NUMBER(20), "POS_AMT_CASH_WITHDRW_X2060" NUMBER(20,2), "AGNT_BC_NO_CASH_WITHDRW_X2070" NUMBER(20), "AGNT_BC_AMT_CASH_WITHDRW_X2080" NUMBER(20,2), "TOT_NO_CBOT_X2090" NUMBER(20), "TOT_AMT_CBOT_X2100" NUMBER(20,2), "TOT_NO_PPI_CLOSED_X2110" NUMBER(20), "TOT_AMT_PPI_CLOSED_X2120" NUMBER(20,2), "TOT_UNSPENT_BAL_PPI_X2130" NUMBER(20,2), "TOT_NO_EXP_PPI_X2140" NUMBER(20), "TOT_AMT_EXP_PPI_X2150" NUMBER(20,2), "TOT_OUT_PPI_X2160" NUMBER(20,2), "FORFEITURE_NO_EXP_PPI__X2170" NUMBER(20), "FORFEITURE_AMT_EXP_PPI_X2180" NUMBER(20,2), "NO_ACTIVE_PPI_X2190" NUMBER(20), "AMT_ACTIVE_PPI_X2200" NUMBER(20,2), "NO_INACTIVE_PPI_X2210" NUMBER(20), "AMT_INACTIVE_PPI_X2220" NUMBER(20,2), "AMT_INACTIVE_PPI_NO_BAL_X2230" NUMBER(20,2), "CB_NO_OUT_PPI_X2240" NUMBER(20), "CB_AMT_OUT_PPI_X2250" NUMBER(20,2), "OUT_LIAB_TWRD_MARCHANT_X2260" NUMBER(20,2), "OUT_BAL_ESCROW_ACC_X2270" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS07_TABLE_1
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS07_TABLE_1" ("SR_NO" NUMBER, "TYPE_OF_MERCHANT" VARCHAR2(1000), "NUMBER_OF_MERCHANT_X010" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS07_TABLE_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS07_TABLE_2" ("SR_NO" NUMBER, "STATE" VARCHAR2(1000), "DISTRICT" VARCHAR2(1000), "SUB_CLASSIFICATION" VARCHAR2(1000), "REGION" VARCHAR2(1000), "ACQUIRING_INFRA" VARCHAR2(1000), "MERCHANT_CAT_ON_BOARDED" VARCHAR2(1000), "NO_OF_TERMINALS_X020" NUMBER(20), "INPUT_NECESSARY_X030" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS07_TABLE_3
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS07_TABLE_3" ("SR_NO" NUMBER, "STATE" VARCHAR2(1000), "DISTRICT" VARCHAR2(1000), "SUB_CLASSIFICATION" VARCHAR2(1000), "REGION" VARCHAR2(1000), "TYPE_OF_PAY_CARD" VARCHAR2(1000), "CARD_NET_PROVIDER" VARCHAR2(1000), "SUB_CLASS_OF_PAY_CARD" VARCHAR2(1000), "NO_OUTSTAND_CARD_X040" NUMBER(20), "NO_OF_CARD_USED_X050" NUMBER(20), "NO_CARD_NO_USED_X060" NUMBER(20), "TYPE_CARD_IFSUB_X070" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS07_TABLE_4
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS07_TABLE_4" ("SR_NO" NUMBER, "STATE" VARCHAR2(1000), "DISTRICT" VARCHAR2(1000), "SUB_CLASSIFICATION" VARCHAR2(1000), "CARD_USE_LOCATION" VARCHAR2(1000), "TYPE_OF_PAY_CARD" VARCHAR2(1000), "TYPE_OF_TRANSACTION" VARCHAR2(1000), "TYPE_OF_ATMPOS_USAGE" VARCHAR2(1000), "VOLUME_X080" NUMBER, "VALUE_X090" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS07_TABLE_5
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS07_TABLE_5" ("SR_NO" NUMBER, "TYPE_OF_PAY_CARD" VARCHAR2(1000), "TYPE_OF_TRANSACTION" VARCHAR2(1000), "TYPE_OF_ATMPOS_USAGE" VARCHAR2(1000), "VOLUME_X100" NUMBER(20), "VALUE_X110" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS07_TABLE_6
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS07_TABLE_6" ("SR_NO" NUMBER, "STATE" VARCHAR2(1000), "DISTRICT" VARCHAR2(1000), "SUB_CLASSIFICATION" VARCHAR2(1000), "CARD_USE_LOCATION" VARCHAR2(1000), "TYPE_OF_PAY_CARD" VARCHAR2(1000), "VOLUME_X120" NUMBER(20), "VALUE_X130" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS07_TABLE_7
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS07_TABLE_7" ("SR_NO" NUMBER, "TYPE_OF_PAY_CARD" VARCHAR2(1000), "VOLUME_X140" NUMBER(20), "VALUE_X150" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS09_TABLE_1
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS09_TABLE_1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "CODE" VARCHAR2(1000), "VOLUME_X010" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS09_TABLE_2
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS09_TABLE_2" ("SR_NO" NUMBER, "DECLINE_DESCR" VARCHAR2(1000), "VOLUME_X020" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS09_TABLE_3
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS09_TABLE_3" ("SR_NO" NUMBER, "DECLINE_DESCR" VARCHAR2(1000), "VOLUME_X030" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS12_RIB_MONTHLY_L1
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS12_RIB_MONTHLY_L1" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(2000), "VAL" NUMBER, "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS12_RIB_MONTHLY_L2
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS12_RIB_MONTHLY_L2" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(2000), "VOLUME_X020" VARCHAR2(30), "VALUE_X030" VARCHAR2(30), "VOLUME_X040" VARCHAR2(30), "VALUE_X050" VARCHAR2(30), "VOLUME_X060" VARCHAR2(30), "VALUE_X070" VARCHAR2(30), "VOLUME_X080" VARCHAR2(30), "VALUE_X090" VARCHAR2(30), "VOLUME_X100" VARCHAR2(30), "VALUE_X110" VARCHAR2(30), "VOLUME_X130" VARCHAR2(30), "VALUE_X140" VARCHAR2(30), "VOLUME_X150" VARCHAR2(30), "VALUE_X160" VARCHAR2(30), "VOLUME_X170" VARCHAR2(30), "VALUE_X180" VARCHAR2(30), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS12_RIB_Q_AUTH_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS12_RIB_Q_AUTH_SIGN" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(2000), "VAL" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS12_RIB_Q_LAYOUT1
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS12_RIB_Q_LAYOUT1" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(2000), "INWARD_REMITTANCES_NO_X010" NUMBER(20,2), "INWARD_REMITTANCES_AMT_X020" NUMBER(20,2), "OUTWARD_REMITTANCES_NO_X030" NUMBER(20,2), "OUTWARD_REMITTANCES_AMT_X040" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS12_RIB_Q_LAYOUT2
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS12_RIB_Q_LAYOUT2" ("SRNO" NUMBER, "CHANNEL" VARCHAR2(2000), "INW_REM_NOS_X050" NUMBER(20,2), "INW_REM_AMT_X060" NUMBER(20,2), "OUT_REM_NOS_X070" NUMBER(20,2), "OUT_REM_AMT_X080" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS12_RIB_Q_LAYOUT3
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS12_RIB_Q_LAYOUT3" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(2000), "INW_REM_NOS_X090" NUMBER(20,2), "INW_REM_AMT_X100" NUMBER(20,2), "OUT_REM_NOS_X110" NUMBER(20,2), "OUT_REM_AMT_X120" NUMBER(20,2), "CHARGES_X130" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS12_RIB_Q_LAYOUT4
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS12_RIB_Q_LAYOUT4" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "INW_REM_NOS_X140" NUMBER(20,2), "INW_REM_AMT_X150" NUMBER(20,2), "OUT_REM_NOS_X160" NUMBER(20,2), "OUT_REM_AMT_X170" NUMBER(20,2), "CHARGES_X180" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS12_RIB_Q_LAYOUT5
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS12_RIB_Q_LAYOUT5" ("SRNO" NUMBER, "NAME_OF_STATES" VARCHAR2(2000), "INW_REM_NOS_X190" NUMBER(20,2), "INW_REM_AMT_X200" NUMBER(20,2), "OUT_REM_NOS_X210" NUMBER(20,2), "OUT_REM_AMT_X220" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS12_RIB_Q_LAYOUT6
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS12_RIB_Q_LAYOUT6" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(2000), "NUMBER_X230" VARCHAR2(40), "AMOUNT_X240" VARCHAR2(40), "REASONS_X250" VARCHAR2(2000), "TRX_COMP_ON_THE_NEXT_DAY_X260" VARCHAR2(40), "TRX_COMP_BEYOND_NEXT_DAY_X270" VARCHAR2(40), "CODE" VARCHAR2(40), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS12_RIB_Q_LAYOUT7
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS12_RIB_Q_LAYOUT7" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(2000), "LAST_DATE_OF_PREV_PERIOD_X280" NUMBER(20,2), "LAST_DATE_OF_PREV_PERIOD_X290" NUMBER(20,2), "LAST_DATE_OF_PREV_PERIOD_X300" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_DPSS12_RIB_Q_LAYOUT8
--------------------------------------------------------

  CREATE TABLE "CIMS_DPSS12_RIB_Q_LAYOUT8" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(2000), "TOTAL_NUMBER_OF_ACCOUNTS_X310" NUMBER(20,2), "NUMBER_OF_TRX_THESE_ACC_X320" NUMBER(20,2), "AVERAGE_BALANCE_THESE_ACC_X330" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FCY_EXPOSURE_STMT
--------------------------------------------------------

  CREATE TABLE "CIMS_FCY_EXPOSURE_STMT" ("SR_NO" NUMBER, "NAME_OF_USER" VARCHAR2(500), "LEI" VARCHAR2(20), "A_T_EXPORT_EXP" NUMBER(20,2), "A_T_EXPORT_AMT_HEDGES" NUMBER(20,2), "A_T_IMPORT_EXP" NUMBER(20,2), "A_T_IMPORT_AMT_HEDGES" NUMBER(20,2), "A_T_SHORT_TERM_EXP" NUMBER(20,2), "A_T_SHORT_TERM_AMT_HEDGES" NUMBER(20,2), "A_NT_EXP" NUMBER(20,2), "A_NT_AMT_HEDGES" NUMBER(20,2), "B_T_EXPORT_AMT_HEDGE" NUMBER(20,2), "B_T_IMPORT_AMT_HEDGE" NUMBER(20,2), "B_NT_AMT_HEDGE" NUMBER(20,2), "INR_FCY_CURR_SWAPS_BASED_ON_RS" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FCY_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_FCY_GEN_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FED01_TABLE_1
--------------------------------------------------------

  CREATE TABLE "CIMS_FED01_TABLE_1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "NO_OF_APP_X010" NUMBER, "AMT_REM_USD_X020" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FED02_PART_A
--------------------------------------------------------

  CREATE TABLE "CIMS_FED02_PART_A" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(500), "NAME_OF_BANK_X010" VARCHAR2(500), "OB_SNRR_X020" VARCHAR2(500), "OB_FCY_X030" VARCHAR2(500), "OB_TOTAL_X040" VARCHAR2(500), "NI_IFF_X050" VARCHAR2(500), "NI_OFF_X060" VARCHAR2(500), "TOT_NI_X070" VARCHAR2(500), "CB_SNRR_X080" VARCHAR2(500), "CB_FCY_X090" VARCHAR2(500), "CB_TOTAL_X100" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FED02_PART_B
--------------------------------------------------------

  CREATE TABLE "CIMS_FED02_PART_B" ("SRNO" NUMBER, "RM_DESCRIPTION" VARCHAR2(500), "CODE" VARCHAR2(500), "COM_PAP_X110" NUMBER(20,2), "NCD_X120" NUMBER(20,2), "COR_BOND_X130" NUMBER(20,2), "MUT_FUNDS_X140" NUMBER(20,2), "TOT_COR_DEBT_X150" NUMBER(20,2), "G_SEC_X160" NUMBER(20,2), "G_TOT_X170" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FED02_PART_C
--------------------------------------------------------

  CREATE TABLE "CIMS_FED02_PART_C" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "VALUE" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FED02_SCOP_QUE
--------------------------------------------------------

  CREATE TABLE "CIMS_FED02_SCOP_QUE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FED04_ANEX_1
--------------------------------------------------------

  CREATE TABLE "CIMS_FED04_ANEX_1" ("SRNO" NUMBER, "NM_ADDRS_FOREIGN_X010" VARCHAR2(500), "PLACE_ADRS_LO_X020" VARCHAR2(500), "EMAIL_CONTACT_LO_X030" VARCHAR2(500), "DT_APPROVAL_LO_X040" VARCHAR2(500), "UIN_X050" VARCHAR2(500), "COUNTRY_INCORP_X060" VARCHAR2(500), "SA_FOREIGN_ENTITY_X070" VARCHAR2(500), "ADD_OFFICE_X080" VARCHAR2(500), "WTHR_UNDER_AUTO_X090" VARCHAR2(500), "RSN_APPROVAL_X100" VARCHAR2(500), "DT_RENEWAL_X110" VARCHAR2(500), "AD_NAME_X120" VARCHAR2(500), "AD_BRNCH_ADRS_X130" VARCHAR2(500), "REMARK_X140" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FED04_ANEX_2
--------------------------------------------------------

  CREATE TABLE "CIMS_FED04_ANEX_2" ("SRNO" NUMBER, "NM_ADDRS_FOREIGN_X010" VARCHAR2(500), "DT_APPROVAL_BO_X020" VARCHAR2(500), "PLACE_ADRS_BO_X030" VARCHAR2(500), "EMAIL_CONTCT_BO_X040" VARCHAR2(500), "UIN_X050" VARCHAR2(500), "COUNTRY_INCORP_X060" VARCHAR2(500), "SA_FOREIGN_ENTITY_X070" VARCHAR2(500), "ACT_BO_X080" VARCHAR2(500), "ADDITION_OFFICE_X090" VARCHAR2(500), "WTHR_UNDER_AUTOMATIC_X100" VARCHAR2(500), "RSN_APPROVAL_X110" VARCHAR2(500), "AD_NAME_X120" VARCHAR2(500), "AD_BRNCH_ADRS_X130" VARCHAR2(500), "REMARK_X140" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FED04_ANEX_3
--------------------------------------------------------

  CREATE TABLE "CIMS_FED04_ANEX_3" ("SRNO" NUMBER, "NM_ADDRS_FOREIGN_X010" VARCHAR2(500), "CUNTRY_INCORP_X020" VARCHAR2(500), "NM_INDIAN_ENTITY_X030" VARCHAR2(500), "PROJ_NAME_X040" VARCHAR2(500), "DT_ESTBLLISMNT_X050" VARCHAR2(500), "ADRS_PO_X060" VARCHAR2(500), "EMAIL_CONTACT_PO_X070" VARCHAR2(500), "AMNT_CONTRCT_X080" NUMBER(20,2), "EXCEPTED_DT_X090" VARCHAR2(500), "WTHR_UNDER_AUTOMATIC_X100" VARCHAR2(500), "CATEGORY_APPROVAL_X110" VARCHAR2(500), "AD_NAME_X120" VARCHAR2(500), "AD_BRNCH_ADRS_X130" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FED05
--------------------------------------------------------

  CREATE TABLE "CIMS_FED05" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "NO_OF_REM_X010" NUMBER, "AMT_USD_X020" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FED06
--------------------------------------------------------

  CREATE TABLE "CIMS_FED06" ("SRNO" NUMBER, "NAME_MINING_CO_X010" VARCHAR2(500), "NAME_IMPORTER_X020" VARCHAR2(500), "IEC_NO_X030" VARCHAR2(500), "AMT_ADV_PMT_X040" NUMBER(20,2), "WH_DOC_EVID_X050" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FED07
--------------------------------------------------------

  CREATE TABLE "CIMS_FED07" ("SRNO" NUMBER, "NAME_IMPORTER_X010" VARCHAR2(500), "IE_CODE_X020" VARCHAR2(500), "PAN_IMPORTER_X030" VARCHAR2(500), "ADDRS_IMPORTER_X040" VARCHAR2(500), "NAME_OVER_SUPP_X050" VARCHAR2(500), "ADDRS_OVER_SUPP_X060" VARCHAR2(500), "AMT_INVOICE_X070" NUMBER(20,2), "CURRENCY_X080" VARCHAR2(500), "DATE_SHIP_X090" VARCHAR2(500), "EXT_PER_DAYS_X100" NUMBER, "BILL_PAID_X110" VARCHAR2(500), "REASON_EXT_X120" VARCHAR2(500), "WHT_IMPO_INVET_X130" VARCHAR2(500), "WHT_IMP_GRNT_EXT_X140" VARCHAR2(500), "WHT_INT_PAY_X150" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FILING_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_FILING_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RETURN_CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMR4_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR4_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE, "SRNO" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_FMR4_NBFC_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR4_NBFC_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMR4_NBFC_SIGN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR4_NBFC_SIGN_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "NAME_DETAILS_MAKER" VARCHAR2(100), "NAME_AUTH_REP_OFFICIAL" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMR4_REP_ROBB_DACO
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR4_REP_ROBB_DACO" ("SR_NO" NUMBER, "BRANCH_CODE" VARCHAR2(200), "NAME_OF_BRANCH" VARCHAR2(200), "ADDRESS_OF_THE_BRANCH" VARCHAR2(200), "DISTRICT" VARCHAR2(200), "STATE" VARCHAR2(200), "TYPE_OF_BRANCH" VARCHAR2(200), "RISK_CLASSIFICATION" VARCHAR2(200), "CURRENCY_CHEST_BRANCH" VARCHAR2(200), "NO_OF_ARMED_GUARDS" NUMBER(20), "CCTV_INSTALLED_AND_WORKING" VARCHAR2(200), "TYPE_OF_CASE" VARCHAR2(200), "PLACE_OF_OCCURRENCE" VARCHAR2(200), "DATE_AND_TIME_OF_OCCURRENCE" VARCHAR2(200), "AMOUNT_INVOLVED" NUMBER(20,2), "AMOUNT_RECOVERED" NUMBER(20,2), "INSURANCE_CLAIM_SETTLED" NUMBER(20,2), "EXTENT_OF_LOSS_TO_THE_BANK" NUMBER(20,2), "WHETHER_STAFF_INVOLVED" VARCHAR2(200), "ACTION_TAKEN_AGAINST_STAFF" VARCHAR2(200), "HUMAN_CASUALTIES" NUMBER(20), "COMPENSATION_PAID_BY_BANK" NUMBER(20,2), "DATE_OF_REPORTING_TO_POLIC" VARCHAR2(200), "POLICE_STATION_NAME" VARCHAR2(200), "MODUS_OPERANDI" VARCHAR2(200), "STEPS_TAKEN_TO_IMPROVE_SYSTEM" VARCHAR2(200), "WHETHER_CASE_CLOSED" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMR4_REP_ROBB_DACO_OLD
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR4_REP_ROBB_DACO_OLD" ("BRANCHCODE" VARCHAR2(200), "NAMEOFBRANCH" VARCHAR2(200), "TYPEOFBRANCH" VARCHAR2(200), "RISKCLASSIFICATION" VARCHAR2(200), "CURRENCYCHESTBRANCH" VARCHAR2(200), "NOOFARMEDGUARDS" NUMBER, "TYPEOFCASE" VARCHAR2(200), "PLACEOFOCCURRENCE" VARCHAR2(200), "DATEANDTIMEOFOCCURRENCE" VARCHAR2(200), "AMOUNTINVOLVED" NUMBER(20,2), "AMOUNTRECOVERED" NUMBER(20,2), "INSURANCECLAIMSETTLED" NUMBER(20,2), "STAFFARRESTED" NUMBER, "ROBBERSARRESTED" NUMBER, "STAFFKILLED" NUMBER, "ROBBERSKILLED" NUMBER, "OTHERSKILLED" NUMBER, "STAFFINJURED" NUMBER, "OTHERSINJURED" NUMBER, "STAFFCONVICTED" NUMBER, "ROBBERSCONVICTED" NUMBER, "COMPENSATIONPAIDTOSTAFF" NUMBER(20,2), "COMPENSATIONPAIDTOOTHERS" NUMBER(20,2), "ACTIONTAKEN" VARCHAR2(200), "CRIMENOPOLICESTATIONNAME" VARCHAR2(200), "MODUSOPERANDI" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMR4_RETURN_ROBBERIES
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR4_RETURN_ROBBERIES" ("NBFC_CODE" VARCHAR2(200), "BRANCH_NAME" VARCHAR2(200), "BRANCH_PLACE" VARCHAR2(200), "BRANCH_STATE" VARCHAR2(200), "BRANCH_DISTRICT" VARCHAR2(200), "BRANCH_PINCODE" NUMBER, "BRANCH_TYPE" VARCHAR2(200), "RISK_CLASSIFICATION" VARCHAR2(200), "NO_ARMED_GUARDS" NUMBER, "TYPE_CASE" VARCHAR2(200), "OCCURANCE_PLACE" VARCHAR2(200), "DATE_TIME_OCCUR" VARCHAR2(200), "AMOUNT_INVOLVED" NUMBER(10,2), "AMOUNT_RECOVERD" NUMBER(10,2), "INSURANCE_CLAIMED_SETT" NUMBER(10,2), "STAFF_ARRESTED" NUMBER, "ROBBERS_ARRESTED" NUMBER, "STAFF_KILLED" NUMBER, "ROBBERS_KILLED" NUMBER, "OTHERS_KILLED" NUMBER, "STAFF_INJURED" NUMBER, "OTHERS_INJURED" NUMBER, "NO_STAFF_CONVICTED" NUMBER, "NO_ROBBERS_CONVICTED" NUMBER, "COMP_PAID_STAFF" NUMBER(10,2), "COMP_PAID_OTHERS" NUMBER(10,2), "ACTION_TAKEN" VARCHAR2(200), "CRIMENO_POLICE_ST_NAME" VARCHAR2(500), "MODUS_OPERANDI" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMR4_SIGN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR4_SIGN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRABOVE1LAKH_2_TBL1
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRABOVE1LAKH_2_TBL1" ("FRAUD_NO" NUMBER, "SRNO" NUMBER, "NAME" VARCHAR2(100), "PAN_OF_STAFF" VARCHAR2(100), "CKYC_NO" VARCHAR2(100), "DESIGNATION" VARCHAR2(100), "TYPE_OF_EXAM" VARCHAR2(100), "SUSPENDED" VARCHAR2(100), "DATE_OF_SUSPENSION" VARCHAR2(100), "DATE_OF_ISSUE_CHARGE" VARCHAR2(100), "DATE_OF_COMMENCE_DOM_ENQ" VARCHAR2(100), "DATE_OF_COMPLETE_ENQ" VARCHAR2(100), "DATE_OF_ISSUE_FINAL_ORDER" VARCHAR2(100), "PUNISHMENT_AWARDED" VARCHAR2(100), "DETAILS_OF_PROSECUTION" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRABOVE1LAKH_2_TBL10
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRABOVE1LAKH_2_TBL10" ("FRAUD_NO" NUMBER, "DESCRIPTION" VARCHAR2(100), "WH_FRAUD_ANY_GRP" VARCHAR2(100), "IF_TRUE_NAME_GRP" VARCHAR2(100), "OTHER" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRABOVE1LAKH_2_TBL11
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRABOVE1LAKH_2_TBL11" ("FRAUD_NO" NUMBER, "DESCRIPTION" VARCHAR2(100), "TPSP" VARCHAR2(100), "IF_TPSP" VARCHAR2(100), "IF_TPSP_REG_NO" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRABOVE1LAKH_2_TBL2
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRABOVE1LAKH_2_TBL2" ("FRAUD_NO" NUMBER, "SRNO" NUMBER, "NAME_OF_ACCOUNT" VARCHAR2(100), "TYPE_OF_ACCOUNT" VARCHAR2(100), "OTHERS" VARCHAR2(100), "ACCOUNT_ADDRESS" VARCHAR2(100), "DATE_OF_SANCTION" VARCHAR2(100), "BORR_ACC_SR_NO" VARCHAR2(100), "SANCTIONED_LIMIT" NUMBER(20,2), "BALANCE_OS" NUMBER(20,2), "PAN_OF_ACCOUNT" VARCHAR2(100), "CIN" VARCHAR2(100), "LEI" VARCHAR2(100), "DATE_OF_NPA" VARCHAR2(100), "CUSTOMER_ID" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRABOVE1LAKH_2_TBL3
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRABOVE1LAKH_2_TBL3" ("FRAUD_NO" NUMBER, "SRNO" NUMBER, "NAME_OF_PERPETRATOR" VARCHAR2(100), "PERPETRATOR_ADDRESS" VARCHAR2(100), "STATUS_OF_PERPETRATOR" VARCHAR2(100), "PAN_OF_PERPETRATOR" VARCHAR2(100), "NAME_OF_ACC_WHR_FRAUD" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRABOVE1LAKH_2_TBL4
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRABOVE1LAKH_2_TBL4" ("FRAUD_NO" NUMBER, "NAME_OF_ACC" VARCHAR2(100), "SR_NO_ACC" NUMBER, "SR_NO" NUMBER, "NAME_OF_DIR_PART" VARCHAR2(100), "PAN_OF_DIR_PART" VARCHAR2(100), "DIN" VARCHAR2(100), "DIR_PART_ADDRESS" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRABOVE1LAKH_2_TBL5
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRABOVE1LAKH_2_TBL5" ("FRAUD_NO" NUMBER, "NAME_OF_ACC" VARCHAR2(100), "SR_NO_ACC" NUMBER, "SR_NO" NUMBER, "NAME_OF_ASSO" VARCHAR2(100), "PAN_OF_ASSO" VARCHAR2(100), "CIN" VARCHAR2(100), "ASSO_ADDRESS" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRABOVE1LAKH_2_TBL6
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRABOVE1LAKH_2_TBL6" ("FRAUD_NO" NUMBER, "NAME_OF_ASSO" VARCHAR2(100), "SR_NO_ASSO" NUMBER, "SR_NO" NUMBER, "NAME_OF_DIR" VARCHAR2(100), "PAN" VARCHAR2(100), "DIN" VARCHAR2(100), "DIR_PROP_ADDRESS" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRABOVE1LAKH_2_TBL7
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRABOVE1LAKH_2_TBL7" ("FRAUD_NO" NUMBER, "SR_NO" NUMBER, "DEATAIL_COLL_SEC" VARCHAR2(100), "VAL_OF_SEC" NUMBER(20,2), "DATE_OF_VALU" VARCHAR2(100), "WHETHER_VALID" VARCHAR2(100), "WHETHER_ENFORCE" VARCHAR2(100), "REMARKS" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRABOVE1LAKH_2_TBL8
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRABOVE1LAKH_2_TBL8" ("FRAUD_NO" NUMBER, "DESCRIPTION" VARCHAR2(100), "WH_FRAUD_REPTD_SCBF" VARCHAR2(100), "IF_TRUE_SCBF" VARCHAR2(100), "COMPLIANCE_SCBF" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRABOVE1LAKH_2_TBL9
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRABOVE1LAKH_2_TBL9" ("FRAUD_NO" NUMBER, "DESCRIPTION" VARCHAR2(100), "WH_FRAUD_GOVT_SCH" VARCHAR2(100), "IF_TRUE_SCHEME" VARCHAR2(100), "OTHER" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRABOVE1LAKH_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRABOVE1LAKH_GEN_INFO" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRABOVE1LAKH_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRABOVE1LAKH_SIGN" ("DESCRIPTION" VARCHAR2(100), "AUTHORISED" VARCHAR2(100), "COUNTERSIGNED" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE, "SRNO" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_FMRABOVE1LAKH_TBL1
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRABOVE1LAKH_TBL1" ("SRNO" NUMBER, "FRAUD_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRABOVE1LAKH_TBL2
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRABOVE1LAKH_TBL2" ("SRNO" NUMBER, "FRAUD_NO" NUMBER, "BANK_NAME" VARCHAR2(200), "OTHER_SPECIFY" VARCHAR2(200), "CONSO_MBA_AMT" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRABOVE1LAKH_TBL3
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRABOVE1LAKH_TBL3" ("SRNO" NUMBER, "FRAUD_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRABOVE1LAKH_TBL4
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRABOVE1LAKH_TBL4" ("SRNO" NUMBER, "FRAUD_NO" NUMBER, "DESCRIPTION" VARCHAR2(4000), "VAL" VARCHAR2(1000), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRBELOW1LAKH_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRBELOW1LAKH_GEN_INFO" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" VARCHAR2(100), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRBELOW1LAKH_PARTD_A
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRBELOW1LAKH_PARTD_A" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(100), "CREDIT_CARDS_NO" NUMBER(10,2), "CREDIT_CARDS_AMT" NUMBER(10,2), "DEBIT_OR_ATM_CARDS_NO" NUMBER(10,2), "DEBIT_OR_ATM_CARDS_AMT" NUMBER(10,2), "INTERNET_BANKING_NO" NUMBER(10,2), "INTERNET_BANKING_AMT" NUMBER(10,2), "UPI_NO" NUMBER(10,2), "UPI_AMT" NUMBER(10,2), "WALLET_OR_PREPAID_CARDS_NO" NUMBER(10,2), "WALLET_OR_PREPAID_CARDS_AMT" NUMBER(10,2), "IMPS_OR_NEFT_OR_RTGS_NO" NUMBER(10,2), "IMPS_OR_NEFT_OR_RTGS_AMT" NUMBER(10,2), "AEPS_OR_OTHER_FRAUDS_NO" NUMBER(10,2), "AEPS_OR_OTHER_FRAUDS_AMT" NUMBER(10,2), "USSD_NO" NUMBER(10,2), "USSD_AMT" NUMBER(10,2), "OTHERS_NO" NUMBER(10,2), "OTHERS_AMT" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRBELOW1LAKH_PARTD_B
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRBELOW1LAKH_PARTD_B" ("SR_NO" VARCHAR2(20), "NEW_TYPE_OF_FRAUD" VARCHAR2(100), "NO_OF_FRAUDS_IN_QUARTER" NUMBER(10,2), "AMT_INVOLVED" NUMBER(10,2), "MODUS_OPERANDI" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRBELOW1LAKH_PARTD_C
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRBELOW1LAKH_PARTD_C" ("SR_NO" VARCHAR2(20), "NEW_TYPE_OF_FRAUD" VARCHAR2(100), "NO_OF_FRAUDS_IN_QUARTER" NUMBER(10,2), "AMT_INVOLVED" NUMBER(10,2), "MODUS_OPERANDI" VARCHAR2(100), "CODE" NUMBER, "REPORTING_DATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRBELOW1LAKH_PART_A
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRBELOW1LAKH_PART_A" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CASES_OUTSTANDING_QUARTER_NO" NUMBER(10,2), "CASES_OUTSTANDING_QUARTER_AMT" NUMBER(10,2), "NEW_CASES_REPORTED_QUARTER_NO" NUMBER(10,2), "NEW_CASES_REPORTED_QUARTER_AMT" NUMBER(10,2), "CASES_CLOSED_CURR_QUARTER_NO" NUMBER(10,2), "CASES_CLOSED_CURR_QUARTER_AMT" NUMBER(10,2), "CASES_OUTSTANDING_END_QUART_NO" NUMBER(10,2), "CASES_OUTSTANDING_END_QUARTER_AMT" NUMBER(10,2), "EXTENT_FRAUDS_CUR_QUARTER_AMT" NUMBER(10,2), "CUMULATIVE_PROVISION_1L_AMT" NUMBER(10,2), "CUMULATIVE_AMT_RECOVERED_1L_AMT" NUMBER(10,2), "CUMULATIVE_AMOUNT_WRITTEN_LT_1L_AMT" NUMBER(10,2), "CUMULATIVE_EXTENT_OF_LOSS_LT_1L_AMT" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRBELOW1LAKH_PART_A_OLD
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRBELOW1LAKH_PART_A_OLD" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CASE_OUT_END_PRE_QAT_NO" NUMBER(20,2), "CASE_OUT_END_PRE_QAT_AMT" NUMBER(20,2), "CASE_RPT_CRNT_QAT_NO" NUMBER(20,2), "CASE_RPT_CRNT_QAT_AMT" NUMBER(20,2), "CASE_CLS_CRNT_QAT_NO" NUMBER(20,2), "CASE_CLS_CRNT_QAT_AMT" NUMBER(20,2), "CASE_OUT_END_QAT_NO" NUMBER(20,2), "CASE_OUT_END_QAT_AMT" NUMBER(20,2), "TOTAL_AMT_RCVR_AMT" NUMBER(20,2), "PRO_HLD_CASE_OUT_END_QAR" NUMBER(20,2), "AMT_RCVR_CRNT_QAT" NUMBER(20,2), "AMT_WRT_OFF_CRNT_QAT" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRBELOW1LAKH_PART_B
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRBELOW1LAKH_PART_B" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(100), "MISAPPROPRIATION_OF_FUNDS_NO" NUMBER(10,2), "MISAPPROPRIATION_OF_FUNDS_AMT" NUMBER(10,2), "FRAUDULENT_ENCASHMENT_FORGED_NO" NUMBER(10,2), "FRAUDULENT_ENCASHMENT_FORGED_AMT" NUMBER(10,2), "MANIPULATION_OF_ACCOUNTS_NO" NUMBER(10,2), "MANIPULATION_OF_ACCOUNTS_AMT" NUMBER(10,2), "CHEATING_CONCEALMENT_IMPERS_NO" NUMBER(10,2), "CHEATING_CONCEALMENT_OR_IMPERS_AMT" NUMBER(10,2), "FORGERY_FOR_FRAUD_DOCS_NO" NUMBER(10,2), "FORGERY_FOR_FRAUD_DOCS_AMT" NUMBER(10,2), "WILFUL_FALSIFICATION_OF_RECORDS_NO" NUMBER(10,2), "WILFUL_FALSIFICATION_OF_RECORDS_AMT" NUMBER(10,2), "FRAUDULENT_CREDIT_GRATIFICATION_NO" NUMBER(10,2), "FRAUDULENT_CREDIT_GRATIFICATION_AMT" NUMBER(10,2), "CASH_SHORTAGES_FRAUD_NO" NUMBER(10,2), "CASH_SHORTAGES_FRAUD_AMT" NUMBER(10,2), "FRAUDULENT_FOREIGN_EXCHANGE_TRNS_NO" NUMBER(10,2), "FRAUDULENT_FOREIGN_EXCHANGE_TRNS_AMT" NUMBER(10,2), "FRAUDULENT_BANKING_ACTIVITIES_NO" NUMBER(10,2), "FRAUDULENT_BANKING_ACTIVITIES_AMT" NUMBER(10,2), "OTHER_FRAUDULENT_ACTIVITIES_NO" NUMBER(10,2), "OTHER_FRAUDULENT_ACTIVITIES_AMT" NUMBER(10,2), "TOTAL_NO" NUMBER(10,2), "TOTAL_AMT" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRBELOW1LAKH_PART_B_OLD
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRBELOW1LAKH_PART_B_OLD" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "MISAPRT_CRI_BREACH_TRUST_NO" NUMBER, "MISAPRT_CRI_BREACH_TRUST_AMT" NUMBER(20,2), "FRD_ENCMNT_BK_ACC_CON_PRO_NO" NUMBER, "FRD_ENCMNT_BK_ACC_CON_PRO_AMT" NUMBER(20,2), "UNAUT_CRDT_FOR_ILLGL_GRTFN_NO" NUMBER, "UNAUT_CRDT_FOR_ILLGL_GRTFN_AMT" NUMBER(20,2), "NEG_CASH_SHRTG_NO" NUMBER, "NEG_CASH_SHRTG_AMT" NUMBER(20,2), "CHEATING_FORGERY_NO" NUMBER, "CHEATING_FORGERY_AMT" NUMBER(20,2), "IRRGLR_FRGN_EXCNG_TNX_NO" NUMBER, "IRRGLR_FRGN_EXCNG_TNX_AMT" NUMBER(20,2), "OTHER_NO" NUMBER, "OTHER_AMT" NUMBER(20,2), "TOTAL_NO" NUMBER, "TOTAL_AMT" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRBELOW1LAKH_PART_C
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRBELOW1LAKH_PART_C" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "STAFF_NO" NUMBER, "STAFF_AMT" NUMBER(20,2), "CUST_NO" NUMBER, "CUST_AMT" NUMBER(20,2), "OUTSIDERS_NO" NUMBER, "OUTSIDERS_AMT" NUMBER(20,2), "STAFF_CUST_NO" NUMBER, "STAFF_CUST_AMT" NUMBER(20,2), "STAFF_OUTSIDERS_NO" NUMBER, "STAFF_OUTSIDERS_AMT" NUMBER(20,2), "CUST_OUTSIDER_NO" NUMBER, "CUST_OUTSIDER_AMT" NUMBER(20,2), "STAFF_CUST_OUTSIDER_NO" NUMBER, "STAFF_CUST_OUTSIDER_AMT" NUMBER(20,2), "TOTAL_NO" NUMBER, "TOTAL_AMT" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRBELOW1LAKH_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRBELOW1LAKH_SIGN" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "NAME_DETAILS_OF_MAKER" VARCHAR2(200), "NAME_OF_AUTH_RPT_OFFICIAL" VARCHAR2(200), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRD03_SCOP_QUE
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRD03_SCOP_QUE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRD03_TABLE1
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRD03_TABLE1" ("SR_NO" NUMBER, "NAME_NR_IMP_EXP" VARCHAR2(1000), "NAME_OVE_BNK" VARCHAR2(1000), "NO_DERI_TR_CANC" NUMBER, "AMT_INVOLVE" NUMBER(20,2), "ACTION_TKN" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRD08
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRD08" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" VARCHAR2(200), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRD09_TABLE_1
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRD09_TABLE_1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "SPOT_CASH_TT_X010" NUMBER(20,4), "FORWARD_X020" NUMBER(20,4), "CANCEL_FORWARD_X030" NUMBER(20,4), "TOTAL_X040" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRD09_TABLE_2
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRD09_TABLE_2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CODE" VARCHAR2(100), "SPOT_X050" NUMBER(20,4), "SWAP_X060" NUMBER(20,4), "FORWARD_X070" NUMBER(20,4), "TOTAL_X080" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRD10_SCOP_QUE
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRD10_SCOP_QUE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRD10_TABLE_1
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRD10_TABLE_1" ("SR_NO" NUMBER, "COMMODITY" VARCHAR2(1000), "MEASURE_UNIT_X010" VARCHAR2(1000), "EXPOSURE_DIRECT_X020" NUMBER(20,4), "EXPOSURE_INDIRECT_X030" NUMBER(20,4), "HEDGES_BOOKED_OTC_X040" NUMBER(20,4), "HEDGES_BOOKED_EXCHANGES_X050" NUMBER(20,4), "GROSS_OUTFLOWS_X060" NUMBER(20,4), "GROSS_INFLOWS_X070" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRD10_TABLE_2
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRD10_TABLE_2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(1000), "SBLC_OS_AMT_X080" NUMBER(20,4), "GUARANTEES_OS_AMT_X090" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMRD10_TABLE_3
--------------------------------------------------------

  CREATE TABLE "CIMS_FMRD10_TABLE_3" ("SR_NO" NUMBER, "GR_DATE" VARCHAR2(1000), "PAN" VARCHAR2(1000), "CUSTOMER" VARCHAR2(1000), "SBLC_GUR_AMT_INVOK_X100" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMR_2_TBL1
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR_2_TBL1" ("FRAUD_NO" NUMBER, "SRNO" NUMBER, "NAME" VARCHAR2(100), "DESIGNATION" VARCHAR2(100), "CKYC_NO" VARCHAR2(100), "PAN_OF_STAFF" VARCHAR2(100), "TYPE_OF_EXAM" VARCHAR2(100), "SUSPENDED" VARCHAR2(100), "DATE_OF_SUSPENSION" VARCHAR2(100), "DATE_OF_ISSUE_CHARGE" VARCHAR2(100), "DATE_OF_COMMENCE_DOM_ENQ" VARCHAR2(100), "DATE_OF_COMPLETE_ENQ" VARCHAR2(100), "DATE_OF_ISSUE_FINAL_ORDER" VARCHAR2(100), "PUNISHMENT_AWARDED" VARCHAR2(100), "DETAILS_OF_PROSECUTION" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMR_2_TBL10
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR_2_TBL10" ("FRAUD_NO" NUMBER, "PARTICULARS" VARCHAR2(100), "WH_FRAUD_ANY_GRP" VARCHAR2(100), "IF_TRUE_NAME_GRP" VARCHAR2(100), "OTHER" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMR_2_TBL11
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR_2_TBL11" ("FRAUD_NO" NUMBER, "PARTICULARS" VARCHAR2(100), "TPSP" VARCHAR2(100), "IF_TPSP" VARCHAR2(100), "IF_TPSP_REG_NO" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMR_2_TBL2
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR_2_TBL2" ("FRAUD_NO" NUMBER, "SRNO" NUMBER, "NAME_OF_ACCOUNT" VARCHAR2(100), "TYPE_OF_ACCOUNT" VARCHAR2(100), "OTHERS" VARCHAR2(100), "ACC_NO" VARCHAR2(100), "ACCOUNT_ADDRESS" VARCHAR2(100), "DATE_OF_SANCTION" VARCHAR2(100), "SANCTIONED_LIMIT" NUMBER(20,2), "BALANCE_OS" NUMBER(20,2), "PAN_ADD_OF_ACCOUNT" VARCHAR2(100), "CIN" VARCHAR2(100), "LEI" VARCHAR2(100), "DATE_OF_NPA" VARCHAR2(100), "CUSTOMER_ID" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMR_2_TBL3
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR_2_TBL3" ("FRAUD_NO" NUMBER, "SRNO" NUMBER, "NAME_OF_PERPETRATOR" VARCHAR2(100), "PERPETRATOR_ADDRESS" VARCHAR2(100), "STATUS_OF_PERPETRATOR" VARCHAR2(100), "PAN_OF_PERPETRATOR" VARCHAR2(100), "NAME_OF_ACC_WHR_FRAUD" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMR_2_TBL4
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR_2_TBL4" ("FRAUD_NO" NUMBER, "NAME_OF_ACC" VARCHAR2(100), "ACC_NO" NUMBER, "SR_NO" NUMBER, "NAME_OF_DIR_PART" VARCHAR2(100), "PAN_OF_DIR_PART" VARCHAR2(100), "DIN" VARCHAR2(100), "DIR_PART_ADDRESS" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMR_2_TBL5
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR_2_TBL5" ("FRAUD_NO" NUMBER, "NAME_OF_ACC" VARCHAR2(100), "ACC_NO" NUMBER, "SR_NO" NUMBER, "NAME_OF_ASSO" VARCHAR2(100), "PAN_OF_ASSO" VARCHAR2(100), "CIN" VARCHAR2(100), "ASSO_ADDRESS" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMR_2_TBL6
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR_2_TBL6" ("FRAUD_NO" NUMBER, "SR_NO_ASSO" NUMBER, "NAME_OF_ASSO" VARCHAR2(100), "SR_NO" NUMBER, "NAME_OF_DIR" VARCHAR2(100), "PAN" VARCHAR2(100), "DIN" VARCHAR2(100), "DIR_PROP_ADDRESS" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMR_2_TBL7
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR_2_TBL7" ("FRAUD_NO" NUMBER, "SR_NO" NUMBER, "DEATAIL_COLL_SEC" VARCHAR2(100), "VAL_OF_SEC" NUMBER(20,2), "DATE_OF_VALU" VARCHAR2(100), "WHETHER_VALID" VARCHAR2(100), "WHETHER_ENFORCE" VARCHAR2(100), "REMARKS" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMR_2_TBL8
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR_2_TBL8" ("FRAUD_NO" NUMBER, "PARTICULARS" VARCHAR2(100), "WH_FRAUD_REPTD_SCBF" VARCHAR2(100), "IF_TRUE_SCBF" VARCHAR2(100), "COMPLIANCE_SCBF" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMR_2_TBL9
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR_2_TBL9" ("FRAUD_NO" NUMBER, "PARTICULARS" VARCHAR2(100), "WH_FRAUD_GOVT_SCH" VARCHAR2(100), "IF_TRUE_SCHEME" VARCHAR2(100), "OTHER" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMR_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR_GEN_INFO" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMR_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR_SIGN" ("DESCRIPTION" VARCHAR2(100), "AUTHORISED" VARCHAR2(100), "COUNTERSIGNED" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE, "SRNO" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_FMR_TBL1
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR_TBL1" ("SRNO" NUMBER, "FRAUD_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMR_TBL2
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR_TBL2" ("SRNO" NUMBER, "FRAUD_NO" NUMBER, "CONS_BANK_NAME" VARCHAR2(200), "AMOUNT" NUMBER(20,2), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_FMR_TBL4
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR_TBL4" ("SRNO" NUMBER, "FRAUD_NO" NUMBER, "DESCRIPTION" VARCHAR2(4000), "VAL" VARCHAR2(1000), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FMR_TBL5
--------------------------------------------------------

  CREATE TABLE "CIMS_FMR_TBL5" ("SRNO" NUMBER, "FRAUD_NO" NUMBER, "PARTICULAR" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORMA_AX_A
--------------------------------------------------------

  CREATE TABLE "CIMS_FORMA_AX_A" ("PARTICULARS" VARCHAR2(500), "OUT_BOOK_VAL" NUMBER, "REV_VAL" NUMBER, "INTEREST" NUMBER, "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORMA_AX_A_HM
--------------------------------------------------------

  CREATE TABLE "CIMS_FORMA_AX_A_HM" ("PARTICULARS" VARCHAR2(500), "OUT_BOOK_VAL" NUMBER, "REV_VAL" NUMBER, "INTEREST" NUMBER, "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORMA_AX_A_HM_Backup
--------------------------------------------------------

  CREATE TABLE "CIMS_FORMA_AX_A_HM_Backup" ("PARTICULARS" VARCHAR2(500), "OUT_BOOK_VAL" NUMBER, "REV_VAL" NUMBER, "INTEREST" NUMBER, "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORMA_AX_B
--------------------------------------------------------

  CREATE TABLE "CIMS_FORMA_AX_B" ("PARTICULARS" VARCHAR2(500), "OUT_BOOK_VAL" NUMBER, "REV_VAL" NUMBER, "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORMA_AX_B_HM
--------------------------------------------------------

  CREATE TABLE "CIMS_FORMA_AX_B_HM" ("PARTICULARS" VARCHAR2(500), "OUT_BOOK_VAL" NUMBER, "REV_VAL" NUMBER, "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORMA_FOOTNOTE_HM
--------------------------------------------------------

  CREATE TABLE "CIMS_FORMA_FOOTNOTE_HM" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORMA_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_FORMA_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORMA_GEN_INFO_HM
--------------------------------------------------------

  CREATE TABLE "CIMS_FORMA_GEN_INFO_HM" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORMA_MAIN
--------------------------------------------------------

  CREATE TABLE "CIMS_FORMA_MAIN" ("PARTICULARS" VARCHAR2(500), "AMOUNT" NUMBER, "CODE" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORMA_MAIN_HM
--------------------------------------------------------

  CREATE TABLE "CIMS_FORMA_MAIN_HM" ("PARTICULARS" VARCHAR2(500), "AMOUNT" NUMBER, "CODE" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORMA_MEMO
--------------------------------------------------------

  CREATE TABLE "CIMS_FORMA_MEMO" ("PARTICULARS" VARCHAR2(500), "AMOUNT" NUMBER, "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORMA_MEMO_HM
--------------------------------------------------------

  CREATE TABLE "CIMS_FORMA_MEMO_HM" ("PARTICULARS" VARCHAR2(500), "AMOUNT" NUMBER, "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORMA_SIGN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_FORMA_SIGN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORMA_SIGN_INFO_HM
--------------------------------------------------------

  CREATE TABLE "CIMS_FORMA_SIGN_INFO_HM" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_ACCT_POLICIES
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_ACCT_POLICIES" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" VARCHAR2(4000), "PY_X020" VARCHAR2(4000), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_ACC_PLY_DIS
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_ACC_PLY_DIS" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" VARCHAR2(4000), "PY_X020" VARCHAR2(4000), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_ADD_DISCLSR
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_ADD_DISCLSR" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" VARCHAR2(2000), "PY_X020" VARCHAR2(2000), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_ASSET_LIA_MGMT
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_ASSET_LIA_MGMT" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(2000), "CY_X010" VARCHAR2(200), "PY_X020" VARCHAR2(200), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_ASSET_LIA_MGMT1
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_ASSET_LIA_MGMT1" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(2000), "D1_CY_X030" NUMBER(20,2), "D1_PY_X040" NUMBER(20,2), "D2_TO_7D_CY_X050" NUMBER(20,2), "D2_TO_7D_PY_X060" NUMBER(20,2), "D8_TO_14D_CY_X070" NUMBER(20,2), "D8_TO_14D_PY_X080" NUMBER(20,2), "D15_TO_30D_CY_X090" NUMBER(20,2), "D15_TO_30D_PY_X100" NUMBER(20,2), "D31_TO_2M_CY_X110" NUMBER(20,2), "D31_TO_2M_PY_X120" NUMBER(20,2), "M2_TO_3M_CY_X130" NUMBER(20,2), "M2_TO_3M_PY_X140" NUMBER(20,2), "M3_TO_6M_CY_X150" NUMBER(20,2), "M3_TO_6M_PY_X160" NUMBER(20,2), "M6_TO_1Y_CY_X170" NUMBER(20,2), "M6_TO_1Y_PY_X180" NUMBER(20,2), "Y1_TO_3Y_CY_X190" NUMBER(20,2), "Y1_TO_3Y_PY_X200" NUMBER(20,2), "Y3_TO_5Y_CY_X210" NUMBER(20,2), "Y3_TO_5Y_PY_X220" NUMBER(20,2), "Y5_CY_X230" NUMBER(20,2), "Y5_PY_X240" NUMBER(20,2), "TOTAL_CY_X250" NUMBER(20,2), "TOTAL_CY_X260" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_ASSET_QUALITY
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_ASSET_QUALITY" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(2000), "CY_X010" VARCHAR2(200), "PY_X020" VARCHAR2(200), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_ASSET_QUALITY1
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_ASSET_QUALITY1" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(2000), "CDR_CY_X030" VARCHAR2(200), "CDR_PY_X040" VARCHAR2(200), "SME_CY_X050" VARCHAR2(200), "SME_PY_X060" VARCHAR2(200), "OTHER_CY_X070" VARCHAR2(200), "OTHER_PY_X080" VARCHAR2(200), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_ASSET_QUALITY2
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_ASSET_QUALITY2" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(2000), "CY_X090" VARCHAR2(200), "PY_X100" VARCHAR2(200), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_ASSET_QUALITY3
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_ASSET_QUALITY3" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(2000), "CY_X110" VARCHAR2(200), "PY_X120" VARCHAR2(200), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_ASSET_QUALITY4
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_ASSET_QUALITY4" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(2000), "CY_X130" NUMBER(20,2), "PY_X140" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_AUDITORS_REPORT
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_AUDITORS_REPORT" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CATE_AUDITOR_X010" VARCHAR2(4000), "NAME_AUDITFITM_X020" VARCHAR2(4000), "NAME_AUDITOR_X030" VARCHAR2(4000), "FIRMS_RE_NO_X040" VARCHAR2(4000), "MEMB_NO_X050" VARCHAR2(4000), "ADD_AUDITORS_X060" VARCHAR2(4000), "PAN_X070" VARCHAR2(4000), "SRN_X080" VARCHAR2(4000), "DATE_SIG_AUDIT_X090" VARCHAR2(4000), "DATE_SIG_BS_X100" VARCHAR2(4000), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_AUDITORS_REPORT_1
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_AUDITORS_REPORT_1" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X110" VARCHAR2(4000), "PY_X120" VARCHAR2(4000), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_BALANCE_SHEET
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_BALANCE_SHEET" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(500), "CODE" VARCHAR2(500), "CY_X010" NUMBER(20,2), "PY_X020" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_BUSS_RATIO
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_BUSS_RATIO" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" VARCHAR2(200), "PY_X020" VARCHAR2(200), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_BUSS_RATIO1
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_BUSS_RATIO1" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X030" NUMBER(20,4), "PY_X040" NUMBER(20,4), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_CAP_ADEQUACY
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_CAP_ADEQUACY" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" VARCHAR2(200), "PY_X020" VARCHAR2(200), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_CASH_FLOW
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_CASH_FLOW" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" NUMBER(20,2), "PY_X020" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_DERIVATIVES
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_DERIVATIVES" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(2000), "CY_X010" VARCHAR2(2000), "PY_X020" VARCHAR2(2000), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_DERIVATIVES1
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_DERIVATIVES1" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(2000), "CY_X030" VARCHAR2(2000), "PY_X040" VARCHAR2(2000), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_DERIVATIVES2
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_DERIVATIVES2" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CY_X050" NUMBER(20,2), "PY_X060" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_DERIVATIVES3
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_DERIVATIVES3" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CY_X070" NUMBER(20,2), "PY_X080" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_DERIVATIVES4
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_DERIVATIVES4" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CY_X090" NUMBER(20,2), "PY_X100" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_DERIVATIVES5
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_DERIVATIVES5" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CY_X110" NUMBER(20,2), "PY_X120" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_DERIVATIVES6
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_DERIVATIVES6" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X130" VARCHAR2(2000), "PY_X140" VARCHAR2(2000), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_DERIVATIVES7
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_DERIVATIVES7" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CURR_DERIV_CY_X150" NUMBER(20,2), "CURR_DERIV_PY_X160" NUMBER(20,2), "INT_RATE_CY_X170" NUMBER(20,2), "INT_RATE_PY_X180" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_EMPLOYEE_DATA
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_EMPLOYEE_DATA" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" NUMBER(20), "PY_X020" NUMBER(20), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_EXPOSR
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_EXPOSR" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" VARCHAR2(200), "PY_X020" VARCHAR2(200), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_EXPOSR1
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_EXPOSR1" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X030" NUMBER(20,2), "PY_X040" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_EXPOSR2
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_EXPOSR2" ("SRNO" NUMBER, "RISK_CATE" VARCHAR2(2000), "CODE" VARCHAR2(200), "EXP_NET_CY_X050" NUMBER(20,2), "EXP_NET_PY_X060" NUMBER(20,2), "PRO_HELD_CY_X070" NUMBER(20,2), "PRO_HELD_PY_X080" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_EXPOSR3
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_EXPOSR3" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "BR1_CY_X090" VARCHAR2(500), "BR1_PY_X100" VARCHAR2(500), "BR2_CY_X110" VARCHAR2(500), "BR2_PY_X120" VARCHAR2(500), "BR3_CY_X130" VARCHAR2(500), "BR3_PY_X140" VARCHAR2(500), "BR4_CY_X150" VARCHAR2(500), "BR4_PY_X160" VARCHAR2(500), "BR5_CY_X170" VARCHAR2(500), "BR5_PY_X180" VARCHAR2(500), "BR6_CY_X190" VARCHAR2(500), "BR6_PY_X200" VARCHAR2(500), "BR7_CY_X210" VARCHAR2(500), "BR7_PY_X220" VARCHAR2(500), "BR8_CY_X230" VARCHAR2(500), "BR8_PY_X240" VARCHAR2(500), "BR9_CY_X250" VARCHAR2(500), "BR9_PY_X260" VARCHAR2(500), "BR10_CY_X270" VARCHAR2(500), "BR10_PY_X280" VARCHAR2(500), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_EXPOSR4
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_EXPOSR4" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X290" VARCHAR2(200), "PY_X300" VARCHAR2(200), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_EXP_IN_EXCESS
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_EXP_IN_EXCESS" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" VARCHAR2(4000), "PY_X020" VARCHAR2(4000), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_EXP_IN_EXCESS1
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_EXP_IN_EXCESS1" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "DTLS_EXP_CY_X030" VARCHAR2(4000), "DTLS_EXP_PY_X040" VARCHAR2(4000), "AMT_CY_X050" NUMBER(20,2), "AMT_PY_X060" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_INVESTMENT
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_INVESTMENT" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" VARCHAR2(200), "PY_X020" VARCHAR2(200), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_MISCELLANEOUS
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_MISCELLANEOUS" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" VARCHAR2(4000), "PY_X020" VARCHAR2(4000), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_NONSLRINVEST_PRT1
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_NONSLRINVEST_PRT1" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(2000), "CY_X010" VARCHAR2(2000), "PY_X020" VARCHAR2(2000), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_NONSLRINVEST_PRT2
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_NONSLRINVEST_PRT2" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "AMT_CY_X030" NUMBER(20,2), "AMT_PY_X040" NUMBER(20,2), "EXT_PRIVATE_PLAC_CY_X050" NUMBER(20,2), "EXT_PRIVATE_PLAC_PY_X060" NUMBER(20,2), "INV_GRADE_SEC_CY_X070" NUMBER(20,2), "INV_GRADE_SEC_PY_X080" NUMBER(20,2), "UNRATED_CY_X090" NUMBER(20,2), "UNRATED_PY_X100" NUMBER(20,2), "UNLISTED_CY_X110" NUMBER(20,2), "UNLISTED_PY_X120" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_NONSLRINVEST_PRT3
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_NONSLRINVEST_PRT3" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X130" NUMBER(20,2), "PY_X140" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_NOTES_ACCOUNTS
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_NOTES_ACCOUNTS" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" VARCHAR2(4000), "PY_X020" VARCHAR2(4000), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_NOTES_ACCOUNTS1
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_NOTES_ACCOUNTS1" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X030" VARCHAR2(4000), "PY_X040" VARCHAR2(4000), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_NOTES_ACCOUNTS2
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_NOTES_ACCOUNTS2" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "PRIN_UNPAID_X050" NUMBER(20,2), "INT_UNPAID_X060" NUMBER(20,2), "TOTAL_UNPAID_X070" NUMBER(20,2), "AMT_MSMED_X080" NUMBER(20,2), "AMT_MADE_SUPPL_X090" NUMBER(20,2), "AMT_INT_X100" NUMBER(20,2), "INT_ACCRUED_X1100" NUMBER(20,2), "FURTHER_INT_X120" NUMBER(20,2), "MAX_AMT_X130" NUMBER(20,2), "NAME_SUPPLIER_X140" NUMBER(20,2), "CIN_X150" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_NOTES_ACCOUNTS3
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_NOTES_ACCOUNTS3" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X160" VARCHAR2(4000), "PY_X170" VARCHAR2(4000), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_PANDL
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_PANDL" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" NUMBER(20,2), "PY_X020" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_PILLAR_3_REQURMT
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_PILLAR_3_REQURMT" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" VARCHAR2(4000), "PY_X020" VARCHAR2(4000), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_RELTD_PARTY
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_RELTD_PARTY" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" VARCHAR2(2000), "PY_X020" VARCHAR2(2000), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_RELTD_PARTY1
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_RELTD_PARTY1" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "PARENT_AMT_CY_X030" NUMBER(20,2), "PARENT_AMT_PY_X040" NUMBER(20,2), "PARENT_MAX_CY_X050" NUMBER(20,2), "PARENT_MAX_PY_X060" NUMBER(20,2), "SUBSIDI_AMT_CY_X070" NUMBER(20,2), "SUBSIDI_AMT_PY_X080" NUMBER(20,2), "SUBSIDI_MAX_CY_X090" NUMBER(20,2), "SUBSIDI_MAX_PY_X100" NUMBER(20,2), "ASSOCIATE_JV_AMT_CY_X110" NUMBER(20,2), "ASSOCIATE_JV_AMT_PY_X120" NUMBER(20,2), "ASSOCIATE_JV_MAX_CY_X130" NUMBER(20,2), "ASSOCIATE_JV_MAX_PY_X140" NUMBER(20,2), "KMP_AMT_CY_X150" NUMBER(20,2), "KMP_AMT_PY_X160" NUMBER(20,2), "KMP_MAX_CY_X170" NUMBER(20,2), "KMP_MAX_PY_X180" NUMBER(20,2), "RELT_KMP_AMT_CY_X190" NUMBER(20,2), "RELT_KMP_AMT_PY_X200" NUMBER(20,2), "RELT_KMP_MAX_CY_X210" NUMBER(20,2), "RELT_KMP_MAX_PY_X220" NUMBER(20,2), "ORP_AMT_CY_X230" NUMBER(20,2), "ORP_AMT_PY_X240" NUMBER(20,2), "ORP_MAX_CY_X250" NUMBER(20,2), "ORP_MAX_PY_X260" NUMBER(20,2), "TOTAL_AMT_CY_X270" NUMBER(20,2), "TOTAL_AMT_PY_X280" NUMBER(20,2), "TOTAL_MAX_CY_X290" NUMBER(20,2), "TOTAL_MAX_PY_X300" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_RELTD_PARTY2
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_RELTD_PARTY2" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "PARENT_CY_X310" NUMBER(20,2), "PARENT_PY_X320" NUMBER(20,2), "SUBSIDI_CY_X330" NUMBER(20,2), "SUBSIDI_PY_X340" NUMBER(20,2), "ASSOCIATE_JV_CY_X350" NUMBER(20,2), "ASSOCIATE_JV_PY_X360" NUMBER(20,2), "KMP_CY_X370" NUMBER(20,2), "KMP_PY_X380" NUMBER(20,2), "RELT_KMP_CY_X390" NUMBER(20,2), "RELT_KMP_PY_X400" NUMBER(20,2), "ORP_CY_X410" NUMBER(20,2), "ORP_PY_X420" NUMBER(20,2), "TOTAL_CY_X430" NUMBER(20,2), "TOTAL_PY_X440" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_REPURCHASE_TRAN1
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_REPURCHASE_TRAN1" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" VARCHAR2(2000), "PY_X020" VARCHAR2(2000), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_REPURCHASE_TRAN2
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_REPURCHASE_TRAN2" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "MIN_OUT_CY_X030" NUMBER(20,2), "MIN_OUT_PY_X040" NUMBER(20,2), "MAX_OUT_CY_X050" NUMBER(20,2), "MAX_OUT_PY_X060" NUMBER(20,2), "DAILY_AVG_CY_X070" NUMBER(20,2), "DAILY_AVG_PY_X080" NUMBER(20,2), "OUT_CY_X090" NUMBER(20,2), "OUT_PY_X100" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SCH1_T_1
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SCH1_T_1" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" NUMBER(20,2), "PY_X020" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SCH1_T_2
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SCH1_T_2" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "NUM_OF_SHARES_CY_X030" NUMBER, "NUM_OF_SHARES_PY_X040" NUMBER, "AMT_OF_PER_SHARE_CAP_CY_X050" NUMBER(20,2), "AMT_OF_PER_SHARE_CAP_PY_X060" NUMBER(20,2), "AMT_OF_CAP_CY_X070" NUMBER(20,2), "AMT_OF_CAP_PY_X080" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SCH_10
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SCH_10" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" NUMBER(20,2), "PY_X020" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SCH_11
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SCH_11" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" NUMBER(20,2), "PY_X020" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SCH_12
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SCH_12" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" NUMBER(20,2), "PY_X020" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SCH_13
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SCH_13" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" NUMBER(20,2), "PY_X020" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SCH_14
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SCH_14" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" NUMBER(20,2), "PY_X020" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SCH_15
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SCH_15" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" NUMBER(20,2), "PY_X020" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SCH_16
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SCH_16" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" NUMBER(20,2), "PY_X020" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SCH_1A
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SCH_1A" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" NUMBER(20,2), "PY_X020" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SCH_2
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SCH_2" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" NUMBER(20,2), "PY_X020" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SCH_2A
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SCH_2A" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" NUMBER(20,2), "PY_X020" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SCH_3
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SCH_3" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" NUMBER(20,2), "PY_X020" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SCH_4
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SCH_4" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" NUMBER(20,2), "PY_X020" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SCH_5
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SCH_5" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" NUMBER(20,2), "PY_X020" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SCH_6
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SCH_6" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" NUMBER(20,2), "PY_X020" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SCH_7
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SCH_7" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" NUMBER(20,2), "PY_X020" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SCH_8
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SCH_8" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" NUMBER(20,2), "PY_X020" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SCH_9
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SCH_9" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_X010" NUMBER(20,2), "PY_X020" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SCOP_QUE
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SCOP_QUE" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(2000), "CODE" VARCHAR2(200), "VALUE" VARCHAR2(2000), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SEC_WISENPA
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SEC_WISENPA" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "CY_GROSS_ADV_X010" NUMBER(20,2), "CY_GROSS_NPA_X020" NUMBER(20,2), "CY_GROSS_NPA_PERC_X030" NUMBER(20,4), "PY_GROSS_ADV_X040" NUMBER(20,2), "PY_GROSS_NPA_X050" NUMBER(20,2), "PY_GROSS_NPA_PERC_X060" NUMBER(20,4), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SEGMENTS
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SEGMENTS" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "TREASURY_CY_X010" NUMBER(20,2), "TREASURY_PY_X020" NUMBER(20,2), "CORP_WB_CY_X030" NUMBER(20,2), "CORP_WB_PY_X040" NUMBER(20,2), "RETAIL_CY_X050" NUMBER(20,2), "RETAIL_PY_X060" NUMBER(20,2), "OTHER_CY_X070" NUMBER(20,2), "OTHER_PY_X080" NUMBER(20,2), "TOTAL_CY_X090" NUMBER(20,2), "TOTAL_PY_X100" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_FR_SEGMENTS1
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_FR_SEGMENTS1" ("SRNO" NUMBER, "PARTICULARS" VARCHAR2(2000), "CODE" VARCHAR2(200), "DOM_CY_X110" NUMBER(20,2), "DOM_PY_X120" NUMBER(20,2), "INT_CY_X130" NUMBER(20,2), "INT_PY_X140" NUMBER(20,2), "TOTAL_CY_X150" NUMBER(20,2), "TOTAL_PY_X160" NUMBER(20,2), "RDATE" DATE, "CONSO_OR_STAND" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_IX_GENINFO
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_IX_GENINFO" ("RDATE" DATE, "DESCRIPTION" VARCHAR2(100), "CODE" VARCHAR2(20), "VALUE" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table CIMS_FORM_IX_MAIN
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_IX_MAIN" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(100), "NO_OF_AC_CURRENT" NUMBER, "AMOUNT_CURRENT" NUMBER, "NO_OF_AC_SAVING" NUMBER, "AMOUNT_SAVING" NUMBER, "NO_OF_AC_FIX" NUMBER, "AMOUNT_FIX" NUMBER, "NO_OF_AC_OD" NUMBER, "AMOUNT_OD" NUMBER, "NO_OF_AC_TOTAL" NUMBER, "AMOUNT_TOTAL" NUMBER, "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_IX_SIGN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_IX_SIGN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_VIII_ANEX1_RBIRETURN
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_VIII_ANEX1_RBIRETURN" ("CODEDESCRIPTION" VARCHAR2(300), "VAL" VARCHAR2(100), "SR_NO" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_VIII_ANEX2_RBIRETURN
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_VIII_ANEX2_RBIRETURN" ("CODEDESCRIPTION" VARCHAR2(300), "VAL" VARCHAR2(100), "SR_NO" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_VIII_ANEX3_RBIRETURN
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_VIII_ANEX3_RBIRETURN" ("CODEDESCRIPTION" VARCHAR2(300), "VAL" VARCHAR2(100), "SR_NO" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_VIII_ANNEX_I
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_VIII_ANNEX_I" ("DAILY_POSITION" VARCHAR2(100), "NET_LIA_SEC_FRT" NUMBER, "SLR_REQUIRED" NUMBER, "GOV_SEC" NUMBER, "OTHER_APPR_SEC" NUMBER, "EXCESS_CASH_BAL_RBI_REQ" NUMBER, "CASH_IN_HAND" NUMBER, "NET_BAL" NUMBER, "AMT_IN_CASH" NUMBER, "BAL_MAINTAIN_RLBANK" NUMBER, "GOLD_VAL" NUMBER, "APPR_SEC_RBI" NUMBER, "TOTAL_SLR" NUMBER, "EXCELL_OR_SHORTFALL" NUMBER, "CODE" VARCHAR2(100), "RDATE" DATE, "SRNO" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_VIII_ANNEX_II
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_VIII_ANNEX_II" ("DATE_OF_FORTNIGHT" VARCHAR2(100), "AVG_CASH_RES" NUMBER, "CASH_BAL_ACT" NUMBER, "PERCENTAGE" NUMBER, "EXCELL_OR_SHORTFALL" NUMBER, "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_VIII_ANNEX_III
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_VIII_ANNEX_III" ("PARTICULARS" VARCHAR2(100), "FACE_VAL" NUMBER, "BOOK_VAL" NUMBER, "DEPRE_HELD" NUMBER, "NET_VAL_SLR" NUMBER, "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_VIII_AUTHO_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_VIII_AUTHO_SIGN" ("DESCRIPTION" VARCHAR2(100), "SIGN_NAME" VARCHAR2(20), "RDATE" DATE, "SR_NO" VARCHAR2(20), "SIGN_DATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_VIII_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_VIII_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_VIII_MAIN
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_VIII_MAIN" ("PARTICULARS" VARCHAR2(500), "FIRST_ALT_FRIDAY" NUMBER, "SECOND_ALT_FRIDAY" NUMBER, "THIRD_ALT_FRIDAY" NUMBER, "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_VIII_MAIN_OTHER
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_VIII_MAIN_OTHER" ("CODEDESCRIPTION" VARCHAR2(300), "VAL" VARCHAR2(20), "SR_NO" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_VIII_MAIN_RPTDATE
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_VIII_MAIN_RPTDATE" ("PARTICULARS" VARCHAR2(500), "FIRST_ALT_FRIDAY" DATE, "SECOND_ALT_FRIDAY" DATE, "THIRD_ALT_FRIDAY" DATE, "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_X_FRN_ASST_LIAB
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_X_FRN_ASST_LIAB" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_X_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_X_GEN_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_X_M_FRN_ASST_LIAB
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_X_M_FRN_ASST_LIAB" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_X_M_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_X_M_GEN_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_X_M_PART_I
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_X_M_PART_I" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_X_M_PART_II
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_X_M_PART_II" ("SR_NO" NUMBER, "PART_2" VARCHAR2(20), "SECURED" NUMBER(18,2), "UNSECURED_CLEAN" NUMBER(18,2), "TOTAL_ADVANCES" NUMBER(18,2), "PERCENTAGE_OF_CLEAN_ADV_TO_TOTAL_ADV" NUMBER(10,4), "TOTAL_DEPOSITS" NUMBER(18,2), "PERCENTAGE_OF_TOTAL_ADV_TO_TOTAL_DEPOSITS" NUMBER(10,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_X_M_PART_III
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_X_M_PART_III" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_X_M_SIGN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_X_M_SIGN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_X_PART_I
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_X_PART_I" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_X_PART_II
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_X_PART_II" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_X_PART_III
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_X_PART_III" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FORM_X_SIGN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_FORM_X_SIGN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FUA_2_TBL1
--------------------------------------------------------

  CREATE TABLE "CIMS_FUA_2_TBL1" ("FRAUD_NO" NUMBER, "SRNO" NUMBER, "NAME" VARCHAR2(100), "PAN_OF_STAFF" VARCHAR2(100), "CKYC_NO" VARCHAR2(100), "DESIGNATION" VARCHAR2(100), "TYPE_OF_EXAM" VARCHAR2(100), "SUSPENDED" VARCHAR2(100), "DATE_OF_SUSPENSION" VARCHAR2(100), "DATE_OF_ISSUE_CHARGE" VARCHAR2(100), "DATE_OF_COMMENCE_DOM_ENQ" VARCHAR2(100), "DATE_OF_COMPLETE_ENQ" VARCHAR2(100), "DATE_OF_ISSUE_FINAL_ORDER" VARCHAR2(100), "PUNISHMENT_AWARDED" VARCHAR2(100), "DETAILS_OF_PROSECUTION" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FUA_2_TBL10
--------------------------------------------------------

  CREATE TABLE "CIMS_FUA_2_TBL10" ("FRAUD_NO" NUMBER, "DESCRIPTION" VARCHAR2(100), "WH_FRAUD_ANY_GRP" VARCHAR2(100), "IF_TRUE_NAME_GRP" VARCHAR2(100), "OTHER" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FUA_2_TBL11
--------------------------------------------------------

  CREATE TABLE "CIMS_FUA_2_TBL11" ("FRAUD_NO" NUMBER, "DESCRIPTION" VARCHAR2(100), "TPSP" VARCHAR2(100), "IF_TPSP" VARCHAR2(100), "IF_TPSP_REG_NO" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FUA_2_TBL2
--------------------------------------------------------

  CREATE TABLE "CIMS_FUA_2_TBL2" ("FRAUD_NO" NUMBER, "SRNO" NUMBER, "NAME_OF_ACCOUNT" VARCHAR2(100), "TYPE_OF_ACCOUNT" VARCHAR2(100), "OTHERS" VARCHAR2(100), "ACCOUNT_ADDRESS" VARCHAR2(100), "DATE_OF_SANCTION" VARCHAR2(100), "BORR_ACC_SR_NO" VARCHAR2(100), "SANCTIONED_LIMIT" NUMBER(20,2), "BALANCE_OS" NUMBER(20,2), "PAN_OF_ACCOUNT" VARCHAR2(100), "CIN" VARCHAR2(100), "LEI" VARCHAR2(100), "DATE_OF_NPA" VARCHAR2(100), "CUSTOMER_ID" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FUA_2_TBL3
--------------------------------------------------------

  CREATE TABLE "CIMS_FUA_2_TBL3" ("FRAUD_NO" NUMBER, "SRNO" NUMBER, "NAME_OF_PERPETRATOR" VARCHAR2(100), "PERPETRATOR_ADDRESS" VARCHAR2(100), "STATUS_OF_PERPETRATOR" VARCHAR2(100), "PAN_OF_PERPETRATOR" VARCHAR2(100), "NAME_OF_ACC_WHR_FRAUD" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FUA_2_TBL4
--------------------------------------------------------

  CREATE TABLE "CIMS_FUA_2_TBL4" ("FRAUD_NO" NUMBER, "NAME_OF_ACC" VARCHAR2(100), "SR_NO_ACC" NUMBER, "SR_NO" NUMBER, "NAME_OF_DIR_PART" VARCHAR2(100), "PAN_OF_DIR_PART" VARCHAR2(100), "DIN" VARCHAR2(100), "DIR_PART_ADDRESS" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FUA_2_TBL5
--------------------------------------------------------

  CREATE TABLE "CIMS_FUA_2_TBL5" ("FRAUD_NO" NUMBER, "NAME_OF_ACC" VARCHAR2(100), "SR_NO_ACC" NUMBER, "SR_NO" NUMBER, "NAME_OF_ASSO" VARCHAR2(100), "PAN_OF_ASSO" VARCHAR2(100), "CIN" VARCHAR2(100), "ASSO_ADDRESS" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FUA_2_TBL6
--------------------------------------------------------

  CREATE TABLE "CIMS_FUA_2_TBL6" ("FRAUD_NO" NUMBER, "NAME_OF_ASSO" VARCHAR2(100), "SR_NO_ASSO" NUMBER, "SR_NO" NUMBER, "NAME_OF_DIR" VARCHAR2(100), "PAN" VARCHAR2(100), "DIN" VARCHAR2(100), "DIR_PROP_ADDRESS" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FUA_2_TBL7
--------------------------------------------------------

  CREATE TABLE "CIMS_FUA_2_TBL7" ("FRAUD_NO" NUMBER, "SR_NO" NUMBER, "DEATAIL_COLL_SEC" VARCHAR2(100), "VAL_OF_SEC" NUMBER(20,2), "DATE_OF_VALU" VARCHAR2(100), "WHETHER_VALID" VARCHAR2(100), "WHETHER_ENFORCE" VARCHAR2(100), "REMARKS" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FUA_2_TBL8
--------------------------------------------------------

  CREATE TABLE "CIMS_FUA_2_TBL8" ("FRAUD_NO" NUMBER, "DESCRIPTION" VARCHAR2(100), "WH_FRAUD_REPTD_SCBF" VARCHAR2(100), "IF_TRUE_SCBF" VARCHAR2(100), "COMPLIANCE_SCBF" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FUA_2_TBL9
--------------------------------------------------------

  CREATE TABLE "CIMS_FUA_2_TBL9" ("FRAUD_NO" NUMBER, "DESCRIPTION" VARCHAR2(100), "WH_FRAUD_GOVT_SCH" VARCHAR2(100), "IF_TRUE_SCHEME" VARCHAR2(100), "OTHER" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FUA_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_FUA_GEN_INFO" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FUA_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_FUA_SIGN" ("DESCRIPTION" VARCHAR2(100), "AUTHORISED" VARCHAR2(100), "COUNTERSIGNED" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE, "SRNO" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_FUA_TBL1
--------------------------------------------------------

  CREATE TABLE "CIMS_FUA_TBL1" ("SRNO" NUMBER, "FRAUD_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FUA_TBL2
--------------------------------------------------------

  CREATE TABLE "CIMS_FUA_TBL2" ("SRNO" NUMBER, "FRAUD_NO" NUMBER, "BANK_NAME" VARCHAR2(200), "OTHER_SPECIFY" VARCHAR2(200), "CONSO_MBA_AMT" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FUA_TBL3
--------------------------------------------------------

  CREATE TABLE "CIMS_FUA_TBL3" ("SRNO" NUMBER, "FRAUD_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_FUA_TBL4
--------------------------------------------------------

  CREATE TABLE "CIMS_FUA_TBL4" ("SRNO" NUMBER, "FRAUD_NO" NUMBER, "DESCRIPTION" VARCHAR2(4000), "VAL" VARCHAR2(1000), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_GPB_FINAL1
--------------------------------------------------------

  CREATE TABLE "CIMS_GPB_FINAL1" ("CODE" NUMBER, "PERTICULARS" VARCHAR2(100), "AMT" VARCHAR2(100), "CURR_AMT" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_GPB_FINAL2
--------------------------------------------------------

  CREATE TABLE "CIMS_GPB_FINAL2" ("CODE" NUMBER, "DURATION" VARCHAR2(100), "AMT_FINAL" NUMBER(30,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_GPB_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_GPB_GEN_INFO" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_IOG_ANNEX_B
--------------------------------------------------------

  CREATE TABLE "CIMS_IOG_ANNEX_B" ("CATGRY_OF_PARTY" VARCHAR2(100), "SL_NO" NUMBER, "NAME_OF_PARTY" VARCHAR2(200), "QNTY_KG" NUMBER, "INVOICE_AMT" NUMBER, "QNTY_KG_CUMM" NUMBER, "INVOICE_AMT_CUMM" NUMBER, "REMARKS" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_IOG_ANNEX_B_GENINFO
--------------------------------------------------------

  CREATE TABLE "CIMS_IOG_ANNEX_B_GENINFO" ("DESCRIPTION" VARCHAR2(100), "VAL" VARCHAR2(100), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_IOG_ANNEX_B_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_IOG_ANNEX_B_SIGN" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_IOG_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_IOG_GEN_INFO" ("SRNO" VARCHAR2(20), "DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_IOG_HY_ANNEX_A
--------------------------------------------------------

  CREATE TABLE "CIMS_IOG_HY_ANNEX_A" ("DESCRIPTION" VARCHAR2(100), "NOMAGNY" NUMBER, "EOUSEZ" NUMBER, "NOMAGNYUSD" NUMBER, "EOUSEZUSD" NUMBER, "NOMAGNYIND" NUMBER, "EOUSEZIND" NUMBER, "RDATE" DATE, "SL_NO" NUMBER, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_IOG_HY_ANNEX_A_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_IOG_HY_ANNEX_A_SIGN" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_IOG_HY_ANNEX_A_TYPE
--------------------------------------------------------

  CREATE TABLE "CIMS_IOG_HY_ANNEX_A_TYPE" ("TRANSACTIONID" NUMBER, "DATEOFTRANSACTION" VARCHAR2(20), "NAMEOFIMPORTER" VARCHAR2(100), "NAMEOFSUPPLIER" VARCHAR2(100), "REFERENCENO" VARCHAR2(100), "QUANTITY" NUMBER, "CURRENCY" VARCHAR2(100), "AMOUNT" NUMBER, "BILLAMOUNT" NUMBER, "TYPE_DESCR" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_IRS_AGGALL_CUR_TGA_PARTB
--------------------------------------------------------

  CREATE TABLE "CIMS_IRS_AGGALL_CUR_TGA_PARTB" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(300), "D1_TO_28D" NUMBER(20,4), "D29_TO_3M" NUMBER(20,4), "OVER_3M_AND_UPTO_6M" NUMBER(20,4), "OVER_6M_AND_UPTO_1Y" NUMBER(20,4), "OVER_1Y_AND_UPTO_3Y" NUMBER(20,4), "OVER_3Y_AND_UPTO_5Y" NUMBER(20,4), "OVER_5Y_AND_UPTO_7Y" NUMBER(20,4), "OVER_7Y_AND_UPTO_10Y" NUMBER(20,4), "OVER_10Y_AND_UPTO_15Y" NUMBER(20,4), "OVER_15Y" NUMBER(20,4), "NON_SENS" NUMBER(20,4), "RSL_RSA_TOTAL" NUMBER(20,4), "TOTAL" NUMBER(20,4), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_IRS_AGG_ALLCUR_TGA_MEMITM
--------------------------------------------------------

  CREATE TABLE "CIMS_IRS_AGG_ALLCUR_TGA_MEMITM" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(300), "HELD_TO_MAT" NUMBER(20,4), "AVAIL_FOR_SALE" NUMBER(20,4), "HELD_FOR_TRADING" NUMBER(20,4), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_IRS_AGG_ALL_CUR_DGA
--------------------------------------------------------

  CREATE TABLE "CIMS_IRS_AGG_ALL_CUR_DGA" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(300), "AMT" NUMBER(20,4), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_IRS_AGG_ALL_CUR_TGA
--------------------------------------------------------

  CREATE TABLE "CIMS_IRS_AGG_ALL_CUR_TGA" ("SR_NO" NUMBER, "MODI_DURA_HFT_AFS_CATA" NUMBER(20,4), "MODI_DURA_TTL_INVT_PORTF" NUMBER(20,4), "PV01_TTL_INVT_PORTF_LTD" NUMBER(20,4), "PV01_TTL_INVT_PORTF" NUMBER(20,4), "OS_BAL_AMOR_AC_SEC_HTM_CATA" NUMBER(20,4), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_IRS_COUPON_YIELD_DGA
--------------------------------------------------------

  CREATE TABLE "CIMS_IRS_COUPON_YIELD_DGA" ("SR_NO" NUMBER, "CURRENCY" VARCHAR2(10), "DESCRIPTION" VARCHAR2(300), "D1_TO_28D_C" NUMBER(20,4), "D1_TO_28D_Y" NUMBER(20,4), "D29_TO_3M_C" NUMBER(20,4), "D29_TO_3M_Y" NUMBER(20,4), "OVER_3M_AND_UPTO_6M_C" NUMBER(20,4), "OVER_3M_AND_UPTO_6M_Y" NUMBER(20,4), "OVER_6M_AND_UPTO_1Y_C" NUMBER(20,4), "OVER_6M_AND_UPTO_1Y_Y" NUMBER(20,4), "OVER_1Y_AND_UPTO_3Y_C" NUMBER(20,4), "OVER_1Y_AND_UPTO_3Y_Y" NUMBER(20,4), "OVER_3Y_AND_UPTO_5Y_C" NUMBER(20,4), "OVER_3Y_AND_UPTO_5Y_Y" NUMBER(20,4), "OVER_5Y_AND_UPTO_7Y_C" NUMBER(20,4), "OVER_5Y_AND_UPTO_7Y_Y" NUMBER(20,4), "OVER_7Y_AND_UPTO_10Y_C" NUMBER(20,4), "OVER_7Y_AND_UPTO_10Y_Y" NUMBER(20,4), "OVER_10Y_AND_UPTO_15Y_C" NUMBER(20,4), "OVER_10Y_AND_UPTO_15Y_Y" NUMBER(20,4), "OVER_15Y_C" NUMBER(20,4), "OVER_15Y_Y" NUMBER(20,4), "NON_SENS_C" NUMBER(20,4), "NON_SENS_Y" NUMBER(20,4), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_IRS_DGA
--------------------------------------------------------

  CREATE TABLE "CIMS_IRS_DGA" ("SR_NO" NUMBER, "CURRENCY" VARCHAR2(10), "DESCRIPTION" VARCHAR2(300), "D1_TO_28D" NUMBER(20,4), "D29_TO_3M" NUMBER(20,4), "OVER_3M_AND_UPTO_6M" NUMBER(20,4), "OVER_6M_AND_UPTO_1Y" NUMBER(20,4), "OVER_1Y_AND_UPTO_3Y" NUMBER(20,4), "OVER_3Y_AND_UPTO_5Y" NUMBER(20,4), "OVER_5Y_AND_UPTO_7Y" NUMBER(20,4), "OVER_7Y_AND_UPTO_10Y" NUMBER(20,4), "OVER_10Y_AND_UPTO_15Y" NUMBER(20,4), "OVER_15Y" NUMBER(20,4), "NON_SENS" NUMBER(20,4), "TOTAL_RSL" NUMBER(20,4), "TOTAL" NUMBER(20,4), "WGT_AVG_MD" NUMBER(20,4), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_IRS_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_IRS_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_IRS_MEMO_TGA_A
--------------------------------------------------------

  CREATE TABLE "CIMS_IRS_MEMO_TGA_A" ("SR_NO" NUMBER, "CURRENCY" VARCHAR2(10), "SR_NO_ID" NUMBER, "DESCRIPTION" VARCHAR2(300), "HELD_TO_MAT" NUMBER(20,4), "AVAIL_FOR_SALE" NUMBER(20,4), "HELD_FOR_TRADING" NUMBER(20,4), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_IRS_MEMO_TGA_B
--------------------------------------------------------

  CREATE TABLE "CIMS_IRS_MEMO_TGA_B" ("SR_NO" NUMBER, "CURRENCY" VARCHAR2(10), "MODI_DURA_HFT_AFS_CATA" NUMBER(20,4), "MODI_DURA_TTL_INVT_PORTF" NUMBER(20,4), "PV01_TTL_INVT_PORTF_LTD" NUMBER(20,4), "PV01_TTL_INVT_PORTF" NUMBER(20,4), "OS_BAL_AMOR_AC_SEC_HTM_CATA" NUMBER(20,4), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_IRS_TGA
--------------------------------------------------------

  CREATE TABLE "CIMS_IRS_TGA" ("SR_NO" NUMBER, "CURRENCY" VARCHAR2(10), "DESCRIPTION" VARCHAR2(300), "D1_TO_28D" NUMBER(20,4), "D29_TO_3M" NUMBER(20,4), "OVER_3M_AND_UPTO_6M" NUMBER(20,4), "OVER_6M_AND_UPTO_1Y" NUMBER(20,4), "OVER_1Y_AND_UPTO_3Y" NUMBER(20,4), "OVER_3Y_AND_UPTO_5Y" NUMBER(20,4), "OVER_5Y_AND_UPTO_7Y" NUMBER(20,4), "OVER_7Y_AND_UPTO_10Y" NUMBER(20,4), "OVER_10Y_AND_UPTO_15Y" NUMBER(20,4), "OVER_15Y" NUMBER(20,4), "NON_SENS" NUMBER(20,4), "TOTAL_RSL" NUMBER(20,4), "TOTAL" NUMBER(20,4), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_LOU_Q_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_LOU_Q_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" NVARCHAR2(40), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_LOU_Q_GURANTY_LETTER
--------------------------------------------------------

  CREATE TABLE "CIMS_LOU_Q_GURANTY_LETTER" ("DESCRIPTION" VARCHAR2(200), "GUR_LTROF_COMRT_BUY_CRDT" NUMBER(20,2), "GUR_LTROF_COMRT_SUPLY_CRDT" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_LOU_Q_SIGN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_LOU_Q_SIGN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_LR_ADD_DETL
--------------------------------------------------------

  CREATE TABLE "CIMS_LR_ADD_DETL" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE, "SRNO" NUMBER, "FREQ" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_LR_CAT_OF_DEPOSITORS
--------------------------------------------------------

  CREATE TABLE "CIMS_LR_CAT_OF_DEPOSITORS" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CUR_DEPOSITS" NUMBER(20,2), "SAVE_DEPOSITS" NUMBER(20,2), "TERM_DEPOSITS" NUMBER(20,2), "TOTAL" NUMBER(20,2), "REMARK" VARCHAR2(100), "CODE" VARCHAR2(100), "FREQ" VARCHAR2(20), "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_LR_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_LR_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE, "SRNO" NUMBER, "FREQ" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_LR_PART_A1
--------------------------------------------------------

  CREATE TABLE "CIMS_LR_PART_A1" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "D1" NUMBER(20,4), "D2TO7" NUMBER(20,4), "D8TO14" NUMBER(20,4), "D15TO30" NUMBER(20,4), "D31TO2M" NUMBER(20,4), "M2TO3" NUMBER(20,4), "M3TO6" NUMBER(20,4), "M6TO1Y" NUMBER(20,4), "Y1TO3" NUMBER(20,4), "Y3TO5" NUMBER(20,4), "Y5TO7" NUMBER(20,4), "Y7TO10" NUMBER(20,4), "Y10TO15" NUMBER(20,4), "OVER15Y" NUMBER(20,4), "OVER5Y" NUMBER(20,4), "TOTAL" NUMBER(20,4), "CODE" VARCHAR2(100), "RDATE" DATE, "FREQ" VARCHAR2(20), "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_LR_PART_A2
--------------------------------------------------------

  CREATE TABLE "CIMS_LR_PART_A2" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "D1" NUMBER(20,2), "D2TO7" NUMBER(20,2), "D8TO14" NUMBER(20,2), "D15TO30" NUMBER(20,2), "D31TO2M" NUMBER(20,2), "M2TO3" NUMBER(20,2), "M3TO6" NUMBER(20,2), "M6TO1Y" NUMBER(20,2), "Y1TO3" NUMBER(20,2), "Y3TO5" NUMBER(20,2), "OVER5Y" NUMBER(20,2), "TOTAL" NUMBER(20,2), "CODE" VARCHAR2(100), "RDATE" DATE, "FREQ" VARCHAR2(20), "CURRENCY" VARCHAR2(20), "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_LR_PART_A3
--------------------------------------------------------

  CREATE TABLE "CIMS_LR_PART_A3" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "D1" NUMBER(20,4), "D2TO7" NUMBER(20,4), "D8TO14" NUMBER(20,4), "D15TO30" NUMBER(20,4), "D31TO2M" NUMBER(20,4), "M2TO3" NUMBER(20,4), "M3TO6" NUMBER(20,4), "M6TO1Y" NUMBER(20,4), "Y1TO3" NUMBER(20,4), "Y3TO5" NUMBER(20,4), "OVER5Y" NUMBER(20,4), "TOTAL" NUMBER(20,4), "CODE" VARCHAR2(100), "RDATE" DATE, "FREQ" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_LR_PART_B1
--------------------------------------------------------

  CREATE TABLE "CIMS_LR_PART_B1" ("SRNO" NUMBER, "COUNTRY" VARCHAR2(20), "DESCRIPTION" VARCHAR2(200), "D1" NUMBER(20,4), "D2TO7" NUMBER(20,4), "D8TO14" NUMBER(20,4), "D15TO30" NUMBER(20,4), "D31TO2M" NUMBER(20,4), "M2TO3" NUMBER(20,4), "M3TO6" NUMBER(20,4), "M6TO1Y" NUMBER(20,4), "Y1TO3" NUMBER(20,4), "Y3TO5" NUMBER(20,4), "OVER5Y" NUMBER(20,4), "TOTAL" NUMBER(20,4), "CODE" VARCHAR2(100), "TYPEID" NUMBER, "FREQ" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_LR_PART_B2
--------------------------------------------------------

  CREATE TABLE "CIMS_LR_PART_B2" ("SRNO" NUMBER, "COUNTRY" VARCHAR2(20), "DESCRIPTION" VARCHAR2(200), "D1" NUMBER(20,4), "D2TO7" NUMBER(20,4), "D8TO14" NUMBER(20,4), "D15TO30" NUMBER(20,4), "D31TO2M" NUMBER(20,4), "M2TO3" NUMBER(20,4), "M3TO6" NUMBER(20,4), "M6TO1Y" NUMBER(20,4), "Y1TO3" NUMBER(20,4), "Y3TO5" NUMBER(20,4), "OVER5Y" NUMBER(20,4), "TOTAL" NUMBER(20,4), "CODE" VARCHAR2(100), "TYPEID" NUMBER, "FREQ" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_LR_PART_C
--------------------------------------------------------

  CREATE TABLE "CIMS_LR_PART_C" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "D1" NUMBER(20,4), "D2TO7" NUMBER(20,4), "D8TO14" NUMBER(20,4), "D1TO14" NUMBER(20,4), "D15TO30" NUMBER(20,4), "D31TO2M" NUMBER(20,4), "M2TO3" NUMBER(20,4), "M3TO6" NUMBER(20,4), "M6TO1Y" NUMBER(20,4), "Y1TO3" NUMBER(20,4), "Y3TO5" NUMBER(20,4), "OVER5Y" NUMBER(20,4), "TOTAL" NUMBER(20,4), "CODE" VARCHAR2(100), "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_LR_SIGN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_LR_SIGN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE, "SRNO" NUMBER, "FREQ" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_LR_TOP20_DEPOSITOR
--------------------------------------------------------

  CREATE TABLE "CIMS_LR_TOP20_DEPOSITOR" ("SRNO" NUMBER, "NAME_OF_DEPOSITOR" VARCHAR2(200), "CATEGORY_OF_DEPOSITOR" VARCHAR2(200), "DESCRIPTION" VARCHAR2(200), "AMOUNT" NUMBER(20,4), "WEIGH_AVG_RATE" NUMBER(20,4), "CODE" VARCHAR2(100), "FREQ" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_LR_TOP20_DEPOSTR_DTL
--------------------------------------------------------

  CREATE TABLE "CIMS_LR_TOP20_DEPOSTR_DTL" ("SRNO" NUMBER, "NAME_OF_DEPOSITOR" VARCHAR2(200), "DESCRIPTION" VARCHAR2(200), "AMOUNT" NUMBER(20,4), "RATE_OF_INTRST" NUMBER(20,4), "DATE_OF_ISSU" VARCHAR2(200), "DATE_OF_MATUR" NVARCHAR2(400), "RESIDUE_MATUR_DAYS" VARCHAR2(200), "CODE" VARCHAR2(100), "FREQ" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_LR_TRM_DEP_AMT_WISE_TB_1
--------------------------------------------------------

  CREATE TABLE "CIMS_LR_TRM_DEP_AMT_WISE_TB_1" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "UP28D_TTL_OUT" NUMBER(20,4), "UP28D_WEIG_AVG_INT_RATE" NUMBER(20,4), "D29TO90_TTL_OUT" NUMBER(20,4), "D29TO90_WEIG_AVG_INT_RATE" NUMBER(20,4), "D91TO180_TTL_OUT" NUMBER(20,4), "D91TO180_WEIG_AVG_INT_RATE" NUMBER(20,4), "D181TO1Y_TTL_OUT" NUMBER(20,4), "D181TO1Y_WEIG_AVG_INT_RATE" NUMBER(20,4), "Y1TO3_TTL_OUT" NUMBER(20,4), "Y1TO3_WEIG_AVG_INT_RATE" NUMBER(20,4), "Y3TO5_TTL_OUT" NUMBER(20,4), "Y3TO5_WEIG_AVG_INT_RATE" NUMBER(20,4), "MORE5Y_TTL_OUT" NUMBER(20,4), "MORE5Y_WEIG_AVG_INT_RATE" NUMBER(20,4), "TOTAL_TTL_OUT" NUMBER(20,4), "TOTAL_WEIG_AVG_INT_RATE" NUMBER(20,4), "CODE" VARCHAR2(100), "FREQ" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_LR_TRM_DEP_AMT_WISE_TB_2
--------------------------------------------------------

  CREATE TABLE "CIMS_LR_TRM_DEP_AMT_WISE_TB_2" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(200), "RUPEE_TRM_DEPOSIT" NUMBER(20,4), "FC_TRM_DEPOSIT" NUMBER(20,4), "TOTAL_OUT_TRM_DEPOSIT" NUMBER(20,4), "CODE" VARCHAR2(100), "FREQ" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD02_INDST_SERVICES
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD02_INDST_SERVICES" ("SRNO" NUMBER, "INDUSTRIES_SELECTED_SERVICES" VARCHAR2(500), "CREDIT" NUMBER(20,2), "INVESTMENT" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD02_INDST_SERVICES_HM
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD02_INDST_SERVICES_HM" ("SRNO" NUMBER, "INDUSTRIES_SELECTED_SERVICES" VARCHAR2(500), "CREDIT" NUMBER(20,2), "INVESTMENT" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD02_MAJOR_SECTORS
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD02_MAJOR_SECTORS" ("SRNO" NUMBER, "SECTOR" VARCHAR2(500), "CREDIT" NUMBER(20,2), "INVESTMENT" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD02_MAJOR_SECTORS_HM
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD02_MAJOR_SECTORS_HM" ("SRNO" NUMBER, "SECTOR" VARCHAR2(500), "CREDIT" NUMBER(20,2), "INVESTMENT" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD02_PRIORITY_SECTOR
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD02_PRIORITY_SECTOR" ("SRNO" NUMBER, "PRIORITY_SECTOR" VARCHAR2(500), "ADVANCES" NUMBER(20,2), "DEPOSIT_OR_INVESTMENT" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD02_PRIORITY_SECTOR_HM
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD02_PRIORITY_SECTOR_HM" ("SRNO" NUMBER, "PRIORITY_SECTOR" VARCHAR2(500), "ADVANCES" NUMBER(20,2), "DEPOSIT_OR_INVESTMENT" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD03_CRR_LAYOUT1
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD03_CRR_LAYOUT1" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(2000), "VAL" NUMBER(20,4), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD03_CRR_LAYOUT1A
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD03_CRR_LAYOUT1A" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(2000), "VAL" NUMBER(20,4), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD03_CRR_LAYOUT1A_HM
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD03_CRR_LAYOUT1A_HM" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(2000), "VAL" NUMBER(20,4), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD03_CRR_LAYOUT1_HM
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD03_CRR_LAYOUT1_HM" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(2000), "VAL" NUMBER(20,4), "CODE" VARCHAR2(20), "RDATE" DATE, "DATE_OF_MONTH" VARCHAR2(1000));

--------------------------------------------------------
--  DDL for Table CIMS_MPD03_CRR_LAYOUT2
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD03_CRR_LAYOUT2" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(2000), "DATES_FOR_FORTNIGHT_X020" VARCHAR2(20), "AVERAGE_CASH_RESERVES_X030" VARCHAR2(20), "CASH_BALANC_ACTUALLY_RBI_X040" VARCHAR2(20), "COL_AS_A_OF_COL2_IN_X050" VARCHAR2(20), "EXCESS_OR_SHORTFALL_X060" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD03_CRR_LAYOUT2_HM
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD03_CRR_LAYOUT2_HM" ("SRNO" NUMBER, "DATES_FOR_FORTNIGHT_X020" VARCHAR2(20), "AVERAGE_CASH_RESERVES_X030" VARCHAR2(20), "CASH_BALANC_ACTUALLY_RBI_X040" VARCHAR2(20), "COL_AS_A_OF_COL2_IN_X050" VARCHAR2(20), "EXCESS_OR_SHORTFALL_X060" VARCHAR2(20), "RDATE" DATE, "CASH_RESERVE_DATE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_MPD03_CRR_LAYOUT3_HM
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD03_CRR_LAYOUT3_HM" ("SRNO" NUMBER, "DESCRIPTION_X020" VARCHAR2(20), "AVERAGE_CASH_RESERVES_X030" VARCHAR2(20), "CASH_BALANC_ACTUALLY_RBI_X040" VARCHAR2(20), "COL_AS_A_OF_COL2_IN_X050" VARCHAR2(20), "EXCESS_OR_SHORTFALL_X060" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD04_SLR_LAYOUT1
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD04_SLR_LAYOUT1" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(2000), "VAL" VARCHAR2(40), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD04_SLR_LAYOUT1_HM
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD04_SLR_LAYOUT1_HM" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(2000), "VAL" VARCHAR2(40), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD04_SLR_LAYOUT2
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD04_SLR_LAYOUT2" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(20), "DAILY_POSITION_DURING_X020" VARCHAR2(30), "NET_DEMAND_TIME_LIABIL_X030" VARCHAR2(30), "SLR_REQUIRED_TO_BE_MAINT_X040" VARCHAR2(30), "GOVERNMENT_SECURITIES_X050" VARCHAR2(30), "OTHER_APPROVE_SECURITIES_X060" VARCHAR2(30), "TREASURY_BILLS_X070" VARCHAR2(30), "EXCESS_CASH_BAL_MAINTAIN_X080" VARCHAR2(30), "CASH_ON_HAND_X090" VARCHAR2(30), "GOLD_X100" VARCHAR2(30), "NET_BAL_WITH_SBI_AND_NOT_X110" VARCHAR2(30), "SECURITIES_DEP_UNDER_ACT_X120" VARCHAR2(30), "AMOUNT_IN_CASH_DEPOSITED_X130" VARCHAR2(30), "APP_SEC_DEPOSIT_WITH_RBI_X140" VARCHAR2(30), "TOTAL_OF_SLR_ACT_MAINTAIN_X150" VARCHAR2(30), "EXCESS_SHORTFALL_IN_SLR_X160" VARCHAR2(30), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD04_SLR_LAYOUT2_HM
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD04_SLR_LAYOUT2_HM" ("SRNO" NUMBER, "CASH_RESERVE_DATE" VARCHAR2(20), "DAILY_POSITION_DURING_X020" VARCHAR2(30), "NET_DEMAND_TIME_LIABIL_X030" VARCHAR2(30), "SLR_REQUIRED_TO_BE_MAINT_X040" VARCHAR2(30), "GOVERNMENT_SECURITIES_X050" VARCHAR2(30), "OTHER_APPROVE_SECURITIES_X060" VARCHAR2(30), "TREASURY_BILLS_X070" VARCHAR2(30), "EXCESS_CASH_BAL_MAINTAIN_X080" VARCHAR2(30), "CASH_ON_HAND_X090" VARCHAR2(30), "GOLD_X100" VARCHAR2(30), "NET_BAL_WITH_SBI_AND_NOT_X110" VARCHAR2(30), "SECURITIES_DEP_UNDER_ACT_X120" VARCHAR2(30), "AMOUNT_IN_CASH_DEPOSITED_X130" VARCHAR2(30), "APP_SEC_DEPOSIT_WITH_RBI_X140" VARCHAR2(30), "TOTAL_OF_SLR_ACT_MAINTAIN_X150" VARCHAR2(30), "EXCESS_SHORTFALL_IN_SLR_X160" VARCHAR2(30), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD04_SLR_LAYOUT3_HM
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD04_SLR_LAYOUT3_HM" ("SRNO" NUMBER, "DESCRIPTION_X020" VARCHAR2(20), "NET_DEMAND_TIME_LIABIL_X030" VARCHAR2(30), "SLR_REQUIRED_TO_BE_MAINT_X040" VARCHAR2(30), "GOVERNMENT_SECURITIES_X050" VARCHAR2(30), "OTHER_APPROVE_SECURITIES_X060" VARCHAR2(30), "TREASURY_BILLS_X070" VARCHAR2(30), "EXCESS_CASH_BAL_MAINTAIN_X080" VARCHAR2(30), "CASH_ON_HAND_X090" VARCHAR2(30), "GOLD_X100" VARCHAR2(30), "NET_BAL_WITH_SBI_AND_NOT_X110" VARCHAR2(30), "SECURITIES_DEP_UNDER_ACT_X120" VARCHAR2(30), "AMOUNT_IN_CASH_DEPOSITED_X130" VARCHAR2(30), "APP_SEC_DEPOSIT_WITH_RBI_X140" VARCHAR2(30), "TOTAL_OF_SLR_ACT_MAINTAIN_X150" VARCHAR2(30), "EXCESS_SHORTFALL_IN_SLR_X160" VARCHAR2(30), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD06_EXT_BEN
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD06_EXT_BEN" ("ITEM" VARCHAR2(200), "CODE" VARCHAR2(20), "AGRI_X010" VARCHAR2(200), "INDUSTRY_X020" VARCHAR2(200), "MSME_X030" VARCHAR2(200), "INFRA_X040" VARCHAR2(200), "TRADE_X050" VARCHAR2(200), "PROF_SERV_X060" VARCHAR2(200), "PERS_HOUS_X070" VARCHAR2(200), "PERS_VEHI_X080" VARCHAR2(200), "PERS_EDU_X090" VARCHAR2(200), "PERS_CREDIT_X100" VARCHAR2(200), "OTH_PERS_LOAN_X110" VARCHAR2(200), "COMM_REAL_EST_X120" VARCHAR2(200), "COMM_VEH_X130" VARCHAR2(200), "RUP_EXP_CREDIT_X140" VARCHAR2(200), "OTHERS_X150" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD06_FOREIGN_CURREXPCRD
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD06_FOREIGN_CURREXPCRD" ("CURRENCY" VARCHAR2(200), "ITEM" VARCHAR2(200), "AMT_OUT_MILLION_X010" NUMBER(20,2), "AMT_OUT_CRORE_X020" NUMBER(20,2), "ROI_MIN_X030" NUMBER(20,4), "ROI_MAX_X040" NUMBER(20,4), "INTERESTRATE_MIN_X050" NUMBER(20,4), "INTERESTRATE_MAX_X060" NUMBER(20,4), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD06_FRESHRUPLOANS_A2
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD06_FRESHRUPLOANS_A2" ("TYPE_OF_CREDIT" VARCHAR2(200), "FRESH_RUPEE_LOANS_X010" NUMBER(20,2), "ROI_MIN_X020" NUMBER(20,4), "ROI_MAX_X030" NUMBER(20,4), "INTERESTRATE_MIN_X040" NUMBER(20,4), "INTERESTRATE_MAX_X050" NUMBER(20,4), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD06_FRESHRUPLOANS_A3
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD06_FRESHRUPLOANS_A3" ("DESCRIPTION" VARCHAR2(200), "VALUE_X060" NUMBER(20,4), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD06_FRESHRUPLOANS_A4
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD06_FRESHRUPLOANS_A4" ("PURPOSE_OF_CREDIT" VARCHAR2(200), "FRESH_RUPEE_LOANS_X070" NUMBER(20,2), "ROI_MIN_X080" NUMBER(20,4), "ROI_MAX_X090" NUMBER(20,4), "INTERESTRATE_MIN_X100" NUMBER(20,4), "INTERESTRATE_MAX_X110" NUMBER(20,4), "WALR_X120" NUMBER(20,4), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD06_FRESHRUPLOANS_A5
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD06_FRESHRUPLOANS_A5" ("SECTOR" VARCHAR2(200), "FRESH_RUPEE_LOANS_X130" NUMBER(20,2), "ROI_MIN_X140" NUMBER(20,4), "ROI_MAX_X150" NUMBER(20,4), "INTERESTRATE_MIN_X160" NUMBER(20,4), "INTERESTRATE_MAX_X170" NUMBER(20,4), "WALR_X180" NUMBER(20,4), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD06_INT_RATE_DOM_SAV_B1
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD06_INT_RATE_DOM_SAV_B1" ("ITEM" VARCHAR2(200), "AMT_OUT_X010" NUMBER(20,2), "INTERESTRATE_MIN_X020" NUMBER(20,4), "INTERESTRATE_MAX_X030" NUMBER(20,4), "WADSDR_X040" NUMBER(20,4), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD06_INT_RATE_DOM_SAV_B2
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD06_INT_RATE_DOM_SAV_B2" ("ITEM" VARCHAR2(200), "DEP_LESS3CR_AMT_OUT_X050" NUMBER(20,2), "DEP_LESS3CR_ROI_MIN_X060" NUMBER(20,4), "DEP_LESS3CR_ROI_MAX_X070" NUMBER(20,4), "DEP_LESS3CR3_DEP_RATE_X080" NUMBER(20,4), "DEP_3CRANDABOVE_AMT_OUT_X090" NUMBER(20,2), "DEP_3CRANDABOVE_ROI_MIN_X100" NUMBER(20,4), "DEP_3CRANDABOVE_ROI_MAX_X110" NUMBER(20,4), "DEP_3CRANDABOVE_DEP_RATE_X120" NUMBER(20,4), "COMBINED_DEP_RATE_X130" NUMBER(20,4), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD06_INT_RATE_DOM_SAV_B2_OLD
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD06_INT_RATE_DOM_SAV_B2_OLD" ("ITEM" VARCHAR2(200), "DEP_LESS2CR_AMT_OUT_X050" NUMBER(20,2), "DEP_LESS2CR_ROI_MIN_X060" NUMBER(20,4), "DEP_LESS2CR_ROI_MAX_X070" NUMBER(20,4), "DEP_LESS2CR3_DEP_RATE_X080" NUMBER(20,4), "DEP_2CRANDABOVE_AMT_OUT_X090" NUMBER(20,2), "DEP_2CRANDABOVE_ROI_MIN_X100" NUMBER(20,4), "DEP_2CRANDABOVE_ROI_MAX_X110" NUMBER(20,4), "DEP_2CRANDABOVE_DEP_RATE_X120" NUMBER(20,4), "COMBINED_DEP_RATE_X130" NUMBER(20,4), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD06_INT_RATE_DOM_SAV_B3
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD06_INT_RATE_DOM_SAV_B3" ("ITEM" VARCHAR2(200), "DEP_LESS3CR_AMT_OUT_X140" NUMBER(20,2), "DEP_LESS3CR_ROI_MIN_X150" NUMBER(20,4), "DEP_LESS3CR_ROI_MAX_X160" NUMBER(20,4), "DEP_LESS3CR3_DEP_RATE_X170" NUMBER(20,4), "DEP_3CRANDABOVE_AMT_OUT_X180" NUMBER(20,2), "DEP_3CRANDABOVE_ROI_MIN_X190" NUMBER(20,4), "DEP_3CRANDABOVE_ROI_MAX_X200" NUMBER(20,4), "DEP_3CRANDABOVE_DEP_RATE_X210" NUMBER(20,4), "COMBINED_DEP_RATE_X220" NUMBER(20,4), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD06_INT_RATE_DOM_SAV_B3_OLD
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD06_INT_RATE_DOM_SAV_B3_OLD" ("ITEM" VARCHAR2(200), "DEP_LESS2CR_AMT_OUT_X140" NUMBER(20,2), "DEP_LESS2CR_ROI_MIN_X150" NUMBER(20,4), "DEP_LESS2CR_ROI_MAX_X160" NUMBER(20,4), "DEP_LESS2CR3_DEP_RATE_X170" NUMBER(20,4), "DEP_2CRANDABOVE_AMT_OUT_X180" NUMBER(20,2), "DEP_2CRANDABOVE_ROI_MIN_X190" NUMBER(20,4), "DEP_2CRANDABOVE_ROI_MAX_X200" NUMBER(20,4), "DEP_2CRANDABOVE_DEP_RATE_X210" NUMBER(20,4), "COMBINED_DEP_RATE_X220" NUMBER(20,4), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD06_NRIDEPOSITS_B4
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD06_NRIDEPOSITS_B4" ("NREDEPOSITS" VARCHAR2(200), "AMT_OUT_X010" NUMBER(20,2), "ROI_MIN_X020" NUMBER(20,4), "ROI_MAX_X030" NUMBER(20,4), "WADR_X040" NUMBER(20,4), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD06_NRIDEPOSITS_FCNR_B5
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD06_NRIDEPOSITS_FCNR_B5" ("CURRENCY" VARCHAR2(200), "ITEM" VARCHAR2(200), "AMT_OUT_MILLION_X050" NUMBER(20,2), "AMT_OUT_CRORE_X060" NUMBER(20,2), "INTERESTRATE_MIN_X070" NUMBER(20,4), "INTERESTRATE_MAX_X080" NUMBER(20,4), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD06_OUTRUPEELOANS
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD06_OUTRUPEELOANS" ("ITEM" VARCHAR2(200), "AMT_OUT_X010" NUMBER(20,2), "ROI_MIN_X020" NUMBER(20,4), "ROI_MAX_X030" NUMBER(20,4), "INTERESTRATE_MIN_X040" NUMBER(20,4), "INTERESTRATE_MAX_X050" NUMBER(20,4), "WALR_X060" NUMBER(20,4), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD07_SCOP_QUE
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD07_SCOP_QUE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD07_TABLE1
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD07_TABLE1" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(2000), "VAL" VARCHAR2(20), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MPD07_TABLE2
--------------------------------------------------------

  CREATE TABLE "CIMS_MPD07_TABLE2" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(2000), "VAL" VARCHAR2(20), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_MTSS
--------------------------------------------------------

  CREATE TABLE "CIMS_MTSS" ("NAME_OF_OVERSEAS_PRINCIPAL" VARCHAR2(100), "TOTL_QUNTMOF_REMIT_RECVD_USD" NUMBER(20,2), "TOTL_QUNTMOF_REMIT_RECVD_INR" NUMBER(20,2), "RDATE" DATE, "SR_NO" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_MTSS_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_MTSS_GEN_INFO" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE, "SR_NO" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_M_FORM_VIII_ANEX1_RBIRETURN
--------------------------------------------------------

  CREATE TABLE "CIMS_M_FORM_VIII_ANEX1_RBIRETURN" ("CODEDESCRIPTION" VARCHAR2(300), "VAL" VARCHAR2(100), "SR_NO" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_M_FORM_VIII_ANEX2_RBIRETURN
--------------------------------------------------------

  CREATE TABLE "CIMS_M_FORM_VIII_ANEX2_RBIRETURN" ("CODEDESCRIPTION" VARCHAR2(300), "VAL" VARCHAR2(100), "SR_NO" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_M_FORM_VIII_ANNEX_I
--------------------------------------------------------

  CREATE TABLE "CIMS_M_FORM_VIII_ANNEX_I" ("DATE_OF_MONTH" VARCHAR2(100), "DAILY_POSITION" VARCHAR2(100), "NET_LIA_SEC_FRT" NUMBER, "SLR_REQUIRED" NUMBER, "GOV_SEC" NUMBER, "OTHER_APPR_SEC" NUMBER, "EXCESS_CASH_BAL_RBI_REQ" NUMBER, "CASH_IN_HAND" NUMBER, "SDF_BALANCES" NUMBER, "NET_BAL" NUMBER, "AMT_IN_CASH" NUMBER, "BAL_MAINTAIN_RLBANK" NUMBER, "GOLD_VAL" NUMBER, "APPR_SEC_RBI" NUMBER, "TOTAL_SLR" NUMBER, "EXCELL_OR_SHORTFALL" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_M_FORM_VIII_ANNEX_II
--------------------------------------------------------

  CREATE TABLE "CIMS_M_FORM_VIII_ANNEX_II" ("DATE_OF_FORTNIGHT" VARCHAR2(100), "AVG_CASH_RES" NUMBER, "CASH_BAL_ACT" NUMBER, "PERCENTAGE" NUMBER, "EXCELL_OR_SHORTFALL" NUMBER, "RDATE" DATE, "DATE_OF_MONTH" VARCHAR2(1000));

--------------------------------------------------------
--  DDL for Table CIMS_M_FORM_VIII_ANNEX_III
--------------------------------------------------------

  CREATE TABLE "CIMS_M_FORM_VIII_ANNEX_III" ("PARTICULARS" VARCHAR2(100), "FACE_VAL" NUMBER, "BOOK_VAL" NUMBER, "DEPRE_HELD" NUMBER, "NET_VAL_SLR" NUMBER, "RDATE" DATE, "CODE" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table CIMS_M_FORM_VIII_ANNEX_III_SECOND
--------------------------------------------------------

  CREATE TABLE "CIMS_M_FORM_VIII_ANNEX_III_SECOND" ("PARTICULARS" VARCHAR2(100), "FACE_VAL" NUMBER, "BOOK_VAL" NUMBER, "DEPRE_HELD" NUMBER, "NET_VAL_SLR" NUMBER, "RDATE" DATE, "CODE" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table CIMS_M_FORM_VIII_ANNEX_II_AVE_TOL
--------------------------------------------------------

  CREATE TABLE "CIMS_M_FORM_VIII_ANNEX_II_AVE_TOL" ("DATE_OF_FORTNIGHT" VARCHAR2(100), "AVG_CASH_RES" NUMBER, "CASH_BAL_ACT" NUMBER, "PERCENTAGE" NUMBER, "EXCELL_OR_SHORTFALL" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_M_FORM_VIII_ANNEX_II_AVE_TOL_SECOND
--------------------------------------------------------

  CREATE TABLE "CIMS_M_FORM_VIII_ANNEX_II_AVE_TOL_SECOND" ("DATE_OF_FORTNIGHT" VARCHAR2(100), "AVG_CASH_RES" NUMBER, "CASH_BAL_ACT" NUMBER, "PERCENTAGE" NUMBER, "EXCELL_OR_SHORTFALL" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_M_FORM_VIII_ANNEX_II_SECOND
--------------------------------------------------------

  CREATE TABLE "CIMS_M_FORM_VIII_ANNEX_II_SECOND" ("DATE_OF_FORTNIGHT" VARCHAR2(100), "AVG_CASH_RES" NUMBER, "CASH_BAL_ACT" NUMBER, "PERCENTAGE" NUMBER, "EXCELL_OR_SHORTFALL" NUMBER, "RDATE" DATE, "DATE_OF_MONTH" VARCHAR2(1000));

--------------------------------------------------------
--  DDL for Table CIMS_M_FORM_VIII_ANNEX_I_AVE_TOL
--------------------------------------------------------

  CREATE TABLE "CIMS_M_FORM_VIII_ANNEX_I_AVE_TOL" ("DAILY_POSITION" VARCHAR2(100), "NET_LIA_SEC_FRT" NUMBER, "SLR_REQUIRED" NUMBER, "GOV_SEC" NUMBER, "OTHER_APPR_SEC" NUMBER, "EXCESS_CASH_BAL_RBI_REQ" NUMBER, "CASH_IN_HAND" NUMBER, "SDF_BALANCES" NUMBER, "NET_BAL" NUMBER, "AMT_IN_CASH" NUMBER, "BAL_MAINTAIN_RLBANK" NUMBER, "GOLD_VAL" NUMBER, "APPR_SEC_RBI" NUMBER, "TOTAL_SLR" NUMBER, "EXCELL_OR_SHORTFALL" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_M_FORM_VIII_ANNEX_I_AVE_TOL_SECOND
--------------------------------------------------------

  CREATE TABLE "CIMS_M_FORM_VIII_ANNEX_I_AVE_TOL_SECOND" ("DAILY_POSITION" VARCHAR2(100), "NET_LIA_SEC_FRT" NUMBER, "SLR_REQUIRED" NUMBER, "GOV_SEC" NUMBER, "OTHER_APPR_SEC" NUMBER, "EXCESS_CASH_BAL_RBI_REQ" NUMBER, "CASH_IN_HAND" NUMBER, "SDF_BALANCES" NUMBER, "NET_BAL" NUMBER, "AMT_IN_CASH" NUMBER, "BAL_MAINTAIN_RLBANK" NUMBER, "GOLD_VAL" NUMBER, "APPR_SEC_RBI" NUMBER, "TOTAL_SLR" NUMBER, "EXCELL_OR_SHORTFALL" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_M_FORM_VIII_ANNEX_I_SECOND
--------------------------------------------------------

  CREATE TABLE "CIMS_M_FORM_VIII_ANNEX_I_SECOND" ("DATE_OF_MONTH" VARCHAR2(100), "DAILY_POSITION" VARCHAR2(100), "NET_LIA_SEC_FRT" NUMBER, "SLR_REQUIRED" NUMBER, "GOV_SEC" NUMBER, "OTHER_APPR_SEC" NUMBER, "EXCESS_CASH_BAL_RBI_REQ" NUMBER, "CASH_IN_HAND" NUMBER, "SDF_BALANCES" NUMBER, "NET_BAL" NUMBER, "AMT_IN_CASH" NUMBER, "BAL_MAINTAIN_RLBANK" NUMBER, "GOLD_VAL" NUMBER, "APPR_SEC_RBI" NUMBER, "TOTAL_SLR" NUMBER, "EXCELL_OR_SHORTFALL" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_M_FORM_VIII_AUTHO_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_M_FORM_VIII_AUTHO_SIGN" ("DESCRIPTION" VARCHAR2(100), "SIGN_NAME" VARCHAR2(100), "RDATE" DATE, "SR_NO" VARCHAR2(20), "SIGN_DATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_M_FORM_VIII_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_M_FORM_VIII_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_M_FORM_VIII_MAIN
--------------------------------------------------------

  CREATE TABLE "CIMS_M_FORM_VIII_MAIN" ("PARTICULARS" VARCHAR2(2000), "FIRST_HALF_MONTH" NUMBER, "SECOND_HALF_MONTH" NUMBER, "RDATE" DATE, "CODE" VARCHAR2(2000));

--------------------------------------------------------
--  DDL for Table CIMS_M_FORM_VIII_MAIN_OTHER
--------------------------------------------------------

  CREATE TABLE "CIMS_M_FORM_VIII_MAIN_OTHER" ("CODEDESCRIPTION" VARCHAR2(300), "VAL" VARCHAR2(45), "SR_NO" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_M_FORM_VIII_MAIN_RPTDATE
--------------------------------------------------------

  CREATE TABLE "CIMS_M_FORM_VIII_MAIN_RPTDATE" ("PARTICULARS" VARCHAR2(500), "FIRST_HALF_MONTH" DATE, "SECOND_HALF_MONTH" DATE, "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_NBFC_RDB_DEFAULT_BORR
--------------------------------------------------------

  CREATE TABLE "CIMS_NBFC_RDB_DEFAULT_BORR" ("SR_NO" NUMBER, "BORROWER_PAN" VARCHAR2(200), "BORROWER_NAME" VARCHAR2(100), "WHETHER_PROJECT_FINANCE" VARCHAR2(100), "DATE_OF_DEFAULT" VARCHAR2(100), "REASON_FOR_CREDIT" VARCHAR2(200), "FUND_AMT_OUTSTAND" NUMBER(20,2), "NON_FUND_AMT_OUTSTAND" NUMBER(20,2), "TOTAL_AMT_OUTSTAND" NUMBER(20,2), "REMARKS" VARCHAR2(200), "TRANSACTION_ID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_NBFC_RDB_DEFAULT_BORR_BACKUP
--------------------------------------------------------

  CREATE TABLE "CIMS_NBFC_RDB_DEFAULT_BORR_BACKUP" ("SR_NO" NUMBER, "BORROWER_PAN" VARCHAR2(200), "BORROWER_NAME" VARCHAR2(100), "DATE_OF_DEFAULT" VARCHAR2(100), "FUND_AMT_OUTSTAND" NUMBER(20,2), "NON_FUND_AMT_OUTSTAND" NUMBER(20,2), "TOTAL_AMT_OUTSTAND" NUMBER(20,2), "REMARKS" VARCHAR2(200), "TRANSACTION_ID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_NBFC_RDB_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_NBFC_RDB_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_NBFC_RDB_OUT_DEFAULT
--------------------------------------------------------

  CREATE TABLE "CIMS_NBFC_RDB_OUT_DEFAULT" ("SR_NO" NUMBER, "BORROWER_PAN" VARCHAR2(200), "BORROWER_NAME" VARCHAR2(100), "WHETHER_PROJECT_FINANCE" VARCHAR2(100), "DT_MOVING_OUT_DEFAULT" VARCHAR2(100), "FUND_AMT_OUTSTAND" NUMBER(20,2), "NON_FUND_AMT_OUTSTAND" NUMBER(20,2), "TOTAL_AMT_OUTSTAND" NUMBER(20,2), "REMARKS" VARCHAR2(200), "TRANSACTION_ID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_NBFC_RDB_OUT_DEFAULT_BACKUP
--------------------------------------------------------

  CREATE TABLE "CIMS_NBFC_RDB_OUT_DEFAULT_BACKUP" ("SR_NO" NUMBER, "BORROWER_PAN" VARCHAR2(200), "BORROWER_NAME" VARCHAR2(100), "DT_MOVING_OUT_DEFAULT" VARCHAR2(100), "FUND_AMT_OUTSTAND" NUMBER(20,2), "NON_FUND_AMT_OUTSTAND" NUMBER(20,2), "TOTAL_AMT_OUTSTAND" NUMBER(20,2), "REMARKS" VARCHAR2(200), "TRANSACTION_ID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_NBFC_RDB_SIGNATORY
--------------------------------------------------------

  CREATE TABLE "CIMS_NBFC_RDB_SIGNATORY" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_NRDCSR_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_NRDCSR_GEN_INFO" ("DESCRIPTION" VARCHAR2(500), "VALUE" VARCHAR2(500), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_NRDCSR_MAIN
--------------------------------------------------------

  CREATE TABLE "CIMS_NRDCSR_MAIN" ("SCHEME" VARCHAR2(100), "ACCOUNT_TYPE" VARCHAR2(100), "ORIGINAL_MATURITY" NUMBER, "REMAINING_MATURITY" NUMBER, "COUNTRY_SWIFT_CODE" VARCHAR2(2), "AC_CURRENCY_SWIFT_CODE" VARCHAR2(3), "RECORD_TYPE_CODE" VARCHAR2(2), "RECORD_AMOUNT" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_NRDCSR_SIGN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_NRDCSR_SIGN_INFO" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_PCI_Q_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_PCI_Q_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_PCI_Q_PARTB_SEC_GROSS_TOT
--------------------------------------------------------

  CREATE TABLE "CIMS_PCI_Q_PARTB_SEC_GROSS_TOT" ("SR_NO" NUMBER, "COUNTRY_CODE" VARCHAR2(10), "BRANCH_CODE" NUMBER(10), "ISSUER_NAME" VARCHAR2(300), "BORR_GRP_NAME" VARCHAR2(200), "SOV_CHAR" VARCHAR2(200), "CATEGORY" VARCHAR2(20), "BOOK_VALUE" NUMBER(20,2), "MKT_VALUE" NUMBER(20,2), "ASSETS_CLASS" VARCHAR2(200), "PROV_HELD_AT_BRANCH" NUMBER(20), "PROV_HELD_AT_HO" NUMBER(20,2), "TOTAL_PROV" NUMBER(20,2), "PROV_REQ_HELD_REG_AUT" NUMBER(20,2), "SHORTFALL" NUMBER(20,2), "HO_SUPP_FUNDS" NUMBER(20,2), "DVL_DRNG_Q" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_PCI_Q_PARTB_TOT_LESS_US
--------------------------------------------------------

  CREATE TABLE "CIMS_PCI_Q_PARTB_TOT_LESS_US" ("SR_NO" NUMBER, "COUNTRY_CODE" VARCHAR2(10), "BRANCH_CODE" NUMBER(10), "ISSUER_NAME" VARCHAR2(300), "BORR_GRP_NAME" VARCHAR2(200), "SOV_CHAR" VARCHAR2(200), "CATEGORY" VARCHAR2(20), "BOOK_VALUE" NUMBER(20,2), "MKT_VALUE" NUMBER(20,2), "ASSETS_CLASS" VARCHAR2(200), "PROV_HELD_AT_BRANCH" NUMBER(20), "PROV_HELD_AT_HO" NUMBER(20,2), "TOTAL_PROV" NUMBER(20,2), "PROV_REQ_HELD_REG_AUT" NUMBER(20,2), "SHORTFALL" NUMBER(20,2), "HO_SUPP_FUNDS" NUMBER(20,2), "DVL_DRNG_Q" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_PCI_Q_PART_A
--------------------------------------------------------

  CREATE TABLE "CIMS_PCI_Q_PART_A" ("SR_NO" NUMBER, "COUNTRY_CODE" VARCHAR2(10), "BRANCH_CODE" NUMBER(10), "BORR_NAME" VARCHAR2(300), "BORR_GRP_NAME" VARCHAR2(200), "INDUSTRY" VARCHAR2(200), "SOV_CHAR" VARCHAR2(200), "CATEGORY" VARCHAR2(20), "TOTA_LTD_SANC" NUMBER(20,2), "FUNDED_LTD_SANC" NUMBER(20,2), "NON_FUNDED_LTD_SANC" NUMBER(20,2), "AMT_OS" NUMBER(20,2), "OF_WHICH_SECU" NUMBER(20,2), "ASSETS_CLASS_AS_PER_HME" VARCHAR2(200), "ASSETS_CLASS_HOST_CNTRY" VARCHAR2(200), "PROV_HELD_AT_HO" NUMBER(20,2), "INT_SUSP" NUMBER(20,2), "TOTAL" NUMBER(20,2), "PROV_REQ_HELD_REG_AUT" NUMBER(20,2), "SHORTFALL" NUMBER(20,2), "HO_SUPP_FUNDS" NUMBER(20,2), "DVL_DRNG_Q" VARCHAR2(200), "RDATE" DATE, "PROV_HELD_AT_BRANCH" NUMBER(20));

--------------------------------------------------------
--  DDL for Table CIMS_PCI_Q_PART_A_SEC2_GRS_TOT
--------------------------------------------------------

  CREATE TABLE "CIMS_PCI_Q_PART_A_SEC2_GRS_TOT" ("SR_NO" NUMBER, "COUNTRY_CODE" VARCHAR2(10), "BRANCH_CODE" NUMBER(10), "BORR_NAME" VARCHAR2(300), "BORR_GRP_NAME" VARCHAR2(200), "INDUSTRY" VARCHAR2(200), "SOV_CHAR" VARCHAR2(200), "CATEGORY" VARCHAR2(20), "TOTA_LTD_SANC" NUMBER(20,2), "FUNDED_LTD_SANC" NUMBER(20,2), "NON_FUNDED_LTD_SANC" NUMBER(20,2), "AMT_OS" NUMBER(20,2), "OF_WHICH_SECU" NUMBER(20,2), "ASSETS_CLASS_AS_PER_HME" VARCHAR2(200), "ASSETS_CLASS_HOST_CNTRY" VARCHAR2(200), "PROV_HELD_AT_HO" NUMBER(20,2), "INT_SUSP" NUMBER(20,2), "TOTAL" NUMBER(20,2), "PROV_REQ_HELD_REG_AUT" NUMBER(20,2), "SHORTFALL" NUMBER(20,2), "HO_SUPP_FUNDS" NUMBER(20,2), "DVL_DRNG_Q" VARCHAR2(200), "RDATE" DATE, "PROV_HELD_AT_BRANCH" NUMBER(20));

--------------------------------------------------------
--  DDL for Table CIMS_PCI_Q_PART_A_TOTAL
--------------------------------------------------------

  CREATE TABLE "CIMS_PCI_Q_PART_A_TOTAL" ("SR_NO" NUMBER, "COUNTRY_CODE" VARCHAR2(10), "BRANCH_CODE" NUMBER(10), "BORR_NAME" VARCHAR2(300), "BORR_GRP_NAME" VARCHAR2(200), "INDUSTRY" VARCHAR2(200), "SOV_CHAR" VARCHAR2(200), "CATEGORY" VARCHAR2(20), "TOTA_LTD_SANC" NUMBER(20,2), "FUNDED_LTD_SANC" NUMBER(20,2), "NON_FUNDED_LTD_SANC" NUMBER(20,2), "AMT_OS" NUMBER(20,2), "OF_WHICH_SECU" NUMBER(20,2), "ASSETS_CLASS_AS_PER_HME" VARCHAR2(200), "ASSETS_CLASS_HOST_CNTRY" VARCHAR2(200), "PROV_HELD_AT_BRANCH" NUMBER(20), "PROV_HELD_AT_HO" NUMBER(20,2), "INT_SUSP" NUMBER(20,2), "TOTAL" NUMBER(20,2), "PROV_REQ_HELD_REG_AUT" NUMBER(20,2), "SHORTFALL" NUMBER(20,2), "HO_SUPP_FUNDS" NUMBER(20,2), "DVL_DRNG_Q" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_PCI_Q_PART_B
--------------------------------------------------------

  CREATE TABLE "CIMS_PCI_Q_PART_B" ("SR_NO" NUMBER, "COUNTRY_CODE" VARCHAR2(10), "BRANCH_CODE" NUMBER(10), "ISSUER_NAME" VARCHAR2(300), "BORR_GRP_NAME" VARCHAR2(200), "SOV_CHAR" VARCHAR2(200), "CATEGORY" VARCHAR2(20), "BOOK_VALUE" NUMBER(20,2), "MKT_VALUE" NUMBER(20,2), "ASSETS_CLASS" VARCHAR2(200), "PROV_HELD_AT_BRANCH" NUMBER(20), "PROV_HELD_AT_HO" NUMBER(20,2), "TOTAL_PROV" NUMBER(20,2), "PROV_REQ_HELD_REG_AUT" NUMBER(20,2), "SHORTFALL" NUMBER(20,2), "HO_SUPP_FUNDS" NUMBER(20,2), "DVL_DRNG_Q" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_PCI_Q_PART_B_TOTAL
--------------------------------------------------------

  CREATE TABLE "CIMS_PCI_Q_PART_B_TOTAL" ("SR_NO" NUMBER, "COUNTRY_CODE" VARCHAR2(10), "BRANCH_CODE" NUMBER(10), "ISSUER_NAME" VARCHAR2(300), "BORR_GRP_NAME" VARCHAR2(200), "SOV_CHAR" VARCHAR2(200), "CATEGORY" VARCHAR2(20), "BOOK_VALUE" NUMBER(20,2), "MKT_VALUE" NUMBER(20,2), "ASSETS_CLASS" VARCHAR2(200), "PROV_HELD_AT_BRANCH" NUMBER(20), "PROV_HELD_AT_HO" NUMBER(20,2), "TOTAL_PROV" NUMBER(20,2), "PROV_REQ_HELD_REG_AUT" NUMBER(20,2), "SHORTFALL" NUMBER(20,2), "HO_SUPP_FUNDS" NUMBER(20,2), "DVL_DRNG_Q" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_PCI_Q_PA_SEC2_TO_LESS_US
--------------------------------------------------------

  CREATE TABLE "CIMS_PCI_Q_PA_SEC2_TO_LESS_US" ("SR_NO" NUMBER, "COUNTRY_CODE" VARCHAR2(10), "BRANCH_CODE" NUMBER(10), "BORR_NAME" VARCHAR2(300), "BORR_GRP_NAME" VARCHAR2(200), "INDUSTRY" VARCHAR2(200), "SOV_CHAR" VARCHAR2(200), "CATEGORY" VARCHAR2(20), "TOTA_LTD_SANC" NUMBER(20,2), "FUNDED_LTD_SANC" NUMBER(20,2), "NON_FUNDED_LTD_SANC" NUMBER(20,2), "AMT_OS" NUMBER(20,2), "OF_WHICH_SECU" NUMBER(20,2), "ASSETS_CLASS_AS_PER_HME" VARCHAR2(200), "ASSETS_CLASS_HOST_CNTRY" VARCHAR2(200), "PROV_HELD_AT_HO" NUMBER(20,2), "INT_SUSP" NUMBER(20,2), "TOTAL" NUMBER(20,2), "PROV_REQ_HELD_REG_AUT" NUMBER(20,2), "SHORTFALL" NUMBER(20,2), "HO_SUPP_FUNDS" NUMBER(20,2), "DVL_DRNG_Q" VARCHAR2(200), "RDATE" DATE, "PROV_HELD_AT_BRANCH" NUMBER(20));

--------------------------------------------------------
--  DDL for Table CIMS_PCI_Q_SIGN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_PCI_Q_SIGN_INFO" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_PDR2_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_PDR2_GEN_INFO" ("SRNO" VARCHAR2(20), "DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_PDR2_SECA_MKTTURNOVR
--------------------------------------------------------

  CREATE TABLE "CIMS_PDR2_SECA_MKTTURNOVR" ("SRNO" VARCHAR2(20), "INDEXNO" VARCHAR2(20), "DESCRIPTION" VARCHAR2(100), "GOI" NUMBER(20,4), "IIBS" NUMBER(20,4), "DEV_LOAN" NUMBER(20,4), "TREASURY_H1" NUMBER(20,4), "TREASURY_H2" NUMBER(20,4), "TOTAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_PDR2_SECB_DUR_MNTH
--------------------------------------------------------

  CREATE TABLE "CIMS_PDR2_SECB_DUR_MNTH" ("SRNO" VARCHAR2(20), "DESCRIPTION" VARCHAR2(100), "NPA_OS_BEGINING" NUMBER(20,2), "NPA_OS_DURING" NUMBER(20,2), "NPA_REVERSE_DURING" NUMBER(20,2), "NPA_OS_END" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_PDR2_SECB_TRADE_POS
--------------------------------------------------------

  CREATE TABLE "CIMS_PDR2_SECB_TRADE_POS" ("SRNO" VARCHAR2(20), "DESCRIPTION" VARCHAR2(100), "NPA" NUMBER(20,2), "MTM" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_PDR2_SECC
--------------------------------------------------------

  CREATE TABLE "CIMS_PDR2_SECC" ("SRNO" VARCHAR2(20), "DESCRIPTION" VARCHAR2(100), "OS_MNTH_END" VARCHAR2(100), "AVG_MNTH_END" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_PDR2_SECD
--------------------------------------------------------

  CREATE TABLE "CIMS_PDR2_SECD" ("SRNO" VARCHAR2(20), "DESCRIPTION" VARCHAR2(100), "NO_GILT_ACC" NUMBER, "TARGET" NUMBER(20,2), "TURNOVER" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_PDR2_SIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_PDR2_SIGN" ("SRNO" VARCHAR2(20), "DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_M_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_M_GEN_INFO" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_M_SEC9_SENSEC_PARTA
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_M_SEC9_SENSEC_PARTA" ("DESCRIPTION" VARCHAR2(200), "EXPOSURE_DOM" NUMBER(20,2), "GROSS_AMT_OS_DOM" NUMBER(20,2), "OF_WHICH_IMPAIRED_DOM" NUMBER(20,2), "EXPOSURE_OVE" NUMBER(20,2), "GROSS_AMT_OS_OVE" NUMBER(20,2), "OF_WHICH_IMPAIRED_OVE" NUMBER(20,2), "CODE" NUMBER(20,2), "RDATE" DATE, "TYPE_ID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_M_SEC9_SENSEC_PARTA_BK
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_M_SEC9_SENSEC_PARTA_BK" ("DESCRIPTION" VARCHAR2(200), "EXPOSURE_DOM" NUMBER(20,2), "GROSS_AMT_OS_DOM" NUMBER(20,2), "OF_WHICH_IMPAIRED_DOM" NUMBER(20,2), "EXPOSURE_OVE" NUMBER(20,2), "GROSS_AMT_OS_OVE" NUMBER(20,2), "OF_WHICH_IMPAIRED_OVE" NUMBER(20,2), "CODE" NUMBER(20,2), "RDATE" DATE, "TYPE_ID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_M_SEC9_SENSEC_PARTB
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_M_SEC9_SENSEC_PARTB" ("DESCRIPTION" VARCHAR2(200), "TOT_EXPO_DOM" NUMBER(20,2), "AMT_OS_FUNDED_DOM" NUMBER(20,2), "RESTRU_STD_DOM" NUMBER(20,2), "IMPAIRED_DOM" NUMBER(20,2), "SLIPPAGE_DOM" NUMBER(20,2), "TOT_EXPO_OVE" NUMBER(20,2), "AMT_OS_FUNDED_OVE" NUMBER(20,2), "RESTRU_STD_OVE" NUMBER(20,2), "IMPAIRED_OVE" NUMBER(20,2), "SLIPPAGE_OVE" NUMBER(20,2), "CODE" NUMBER(20), "TYPEID" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_M_SEC9_SENSEC_PARTB_bckup
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_M_SEC9_SENSEC_PARTB_bckup" ("DESCRIPTION" VARCHAR2(200), "TOT_EXPO_DOM" NUMBER(20,2), "AMT_OS_FUNDED_DOM" NUMBER(20,2), "RESTRU_STD_DOM" NUMBER(20,2), "IMPAIRED_DOM" NUMBER(20,2), "SLIPPAGE_DOM" NUMBER(20,2), "TOT_EXPO_OVE" NUMBER(20,2), "AMT_OS_FUNDED_OVE" NUMBER(20,2), "RESTRU_STD_OVE" NUMBER(20,2), "IMPAIRED_OVE" NUMBER(20,2), "SLIPPAGE_OVE" NUMBER(20,2), "CODE" NUMBER(20), "TYPEID" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_M_SIGN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_M_SIGN_INFO" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_GEN_INFO" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC10
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC10" ("DESCRIPTION" VARCHAR2(100), "FUN_EXP" NUMBER(20,2), "NON_FUN_EXP" NUMBER(20,2), "TOTAL" NUMBER(20,2), "AMT_OUT_FUN" NUMBER(20,2), "OF_WHC_IMPAIR" NUMBER(20,2), "LOSS_PRO_HELD" NUMBER(20,2), "INT_MIN" NUMBER(20,2), "INT_MAX" NUMBER(20,2), "INT_WGT_AVG_RATE" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC11
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC11" ("COUNTRY_BRW_CUNTR_PARTY" VARCHAR2(100), "COUNTRY_RISK" VARCHAR2(100), "SECTOR" VARCHAR2(100), "STD" NUMBER(20,2), "SUB_STD" NUMBER(20,2), "DOUBTFUL" NUMBER(20,2), "LOSS" NUMBER(20,2), "TOTAL" NUMBER(20,2), "OF_SHRT_TR_EXP" NUMBER(20,2), "NET_FUND_TOTAL" NUMBER(20,2), "NET_FUND_OF_SHRT_TR_EXP" NUMBER(20,2), "GR_NONFUND_EXP" NUMBER(20,2), "PROV_HELD_COUNTRY" NUMBER(20,2), "PRO_AS_NET_FUND" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC1_EXC_GOVT_PAPER
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC1_EXC_GOVT_PAPER" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC1_LAST_DATE_PORT
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC1_LAST_DATE_PORT" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC1_PART_A_DOM
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC1_PART_A_DOM" ("PERIOD_DELINQUENCY" VARCHAR2(200), "TERM_LOAN" NUMBER(20,2), "CASH_CR_OVERDRAFT_DEMAND_LOAN" NUMBER(20,2), "BILLS_PURCHASE_DISCOUNT" NUMBER(20,2), "LOAN_ADVANCE_BANK" NUMBER(20,2), "TOTAL_LOAN_ASSETS" NUMBER(20,2), "CODE" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC1_PART_B_DOM
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC1_PART_B_DOM" ("PERIOD_DELINQUENCY" VARCHAR2(200), "COMMERCIAL_PAPER" NUMBER(20,2), "NOTE_BONDS_CORPORATE" NUMBER(20,2), "INTER_BANK_ASSETS" NUMBER(20,2), "LEASE_EASE_RECEIVABLE" NUMBER(20,2), "OTHERS" NUMBER(20,2), "TOTAL_OIBA" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC1_PART_C_O
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC1_PART_C_O" ("PERIOD_DELINQUENCY" VARCHAR2(200), "TERM_LOAN" NUMBER(20,2), "CASH_CR_OVERDRAFT_DEMAND_LOAN" NUMBER(20,2), "BILLS_PURCHASE_DISCOUNT" NUMBER(20,2), "LOAN_ADVANCE_BANK" NUMBER(20,2), "TOTAL_LOAN_ASSETS" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC1_PART_D_O
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC1_PART_D_O" ("PERIOD_DELINQUENCY" VARCHAR2(200), "COMMERCIAL_PAPER" NUMBER(20,2), "NOTE_BONDS_CORPORATE" NUMBER(20,2), "INTER_BANK_ASSETS" NUMBER(20,2), "OTHERS" NUMBER(20,2), "TOTAL_OIBA" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC2_LAST_DATE_PORT
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC2_LAST_DATE_PORT" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC2_PART_A
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC2_PART_A" ("RISK_CATEGORY" VARCHAR2(200), "OUTSTANDING_AMT_DOM" NUMBER(20,2), "PER_TO_TOTAL_DOM" NUMBER(20,4), "PROVISION_MADE_LOSSES_DOM" NUMBER(20,2), "OUTSTANDING_AMT_O" NUMBER(20,2), "PER_TO_TOTAL_O" NUMBER(20,4), "PROVISION_MADE_LOSSES_O" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC2_PART_A_MEMO
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC2_PART_A_MEMO" ("MEMORANDUM_ITEM" VARCHAR2(200), "OUTSTANDING_AMT_DOM" NUMBER(20,2), "OUTSTANDING_AMT_O" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC2_PART_A_NPA
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC2_PART_A_NPA" ("RISK_CATEGORY" VARCHAR2(200), "OUTSTANDING_AMT_DOM" NUMBER(20,2), "OUTSTANDING_AMT_O" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC2_PART_B
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC2_PART_B" ("MOVEMENT_PROVISION_NPA" VARCHAR2(200), "DOMESTIC" NUMBER(20,2), "OVERSEAS" NUMBER(20,2), "GLOBAL" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC2_PART_C
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC2_PART_C" ("ITEM" VARCHAR2(200), "STANDARD_DOM" NUMBER(20,2), "SUBSTANDARD_DOM" NUMBER(20,2), "DOUBTFUL_DOM" NUMBER(20,2), "LOSS_DOM" NUMBER(20,2), "TOTAL_DOM" NUMBER(20,2), "STANDARD_O" NUMBER(20,2), "SUBSTANDARD_O" NUMBER(20,2), "DOUBTFUL_O" NUMBER(20,2), "LOSS_O" NUMBER(20,2), "TOTAL_O" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC3_PART_A
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC3_PART_A" ("CATEGORY" VARCHAR2(200), "DESCRIPTION" VARCHAR2(200), "ACC_RES_DOM" NUMBER(20,2), "ACC_RES_CDR_DOM" NUMBER(20,2), "OUT_ACC_RES_DOM" NUMBER(20,2), "OUT_ACC_RES_CDR_DOM" NUMBER(20,2), "ACC_SLIP_DOM" NUMBER(20,2), "OUT_ACC_SLIP_DOM" NUMBER(20,2), "ACC_RES_OS" NUMBER(20,2), "ACC_RES_CDR_OS" NUMBER(20,2), "OUT_ACC_RES_OS" NUMBER(20,2), "OUT_ACC_RES_CDR_OS" NUMBER(20,2), "ACC_SLIP_OS" NUMBER(20,2), "OUT_ACC_SLIP_OS" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC3_PART_B
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC3_PART_B" ("MOVEMENT_RESTRUCTURE_STD_LA" VARCHAR2(200), "DOMESTIC" NUMBER(20,2), "OVERSEAS" NUMBER(20,2), "GLOBAL" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE, "TYPE_ID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC4_PART_A
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC4_PART_A" ("MOVEMENT_FROM" VARCHAR2(200), "STANDARD_DOM" NUMBER(20,2), "SUBSTANDARD_DOM" NUMBER(20,2), "DOUBTFUL_DOM" NUMBER(20,2), "LOSS_DOM" NUMBER(20,2), "TOTAL_DOM" NUMBER(20,2), "STANDARD_O" NUMBER(20,2), "SUBSTANDARD_O" NUMBER(20,2), "DOUBTFUL_O" NUMBER(20,2), "LOSS_O" NUMBER(20,2), "TOTAL_O" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC4_PART_B
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC4_PART_B" ("MOVEMENT_FROM" VARCHAR2(200), "SUBSTANDARD_DOM" NUMBER(20,2), "DOUBTFUL_DOM" NUMBER(20,2), "LOSS_DOM" NUMBER(20,2), "TOTAL_DOM" NUMBER(20,2), "SUBSTANDARD_O" NUMBER(20,2), "DOUBTFUL_O" NUMBER(20,2), "LOSS_O" NUMBER(20,2), "TOTAL_O" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC4_PART_C
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC4_PART_C" ("DESCRIPTION" VARCHAR2(200), "DOMESTIC" NUMBER(20,2), "OVERSEAS" NUMBER(20,2), "GLODAL" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC4_PART_D
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC4_PART_D" ("DESCRIPTION" VARCHAR2(200), "NO_OF_CASE" NUMBER(20,2), "AMOUNT" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC5_TOP_CR
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC5_TOP_CR" ("SR_NO" NUMBER, "PAN_DEFAULTER" VARCHAR2(200), "NAME_DEFAULTER" VARCHAR2(200), "DATE_SANCTION" VARCHAR2(200), "RISK_CLASSIFICATION" VARCHAR2(100), "FUND_CR_EXP" NUMBER(20,2), "NONFUND_CR_EXP" NUMBER(20,2), "TOTAL_CR_EXP" NUMBER(20,2), "LOSS_PRO_HELD" NUMBER(20,2), "INTR_ARREARS" NUMBER(20,2), "TOTAL_INV_EXP_IF" NUMBER(20,2), "TOTAL_EXP" NUMBER(20,2), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC5_TOP_CR_TL
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC5_TOP_CR_TL" ("DESCRIPTION" VARCHAR2(200), "FUND_CR_EXP" NUMBER(20,2), "NONFUND_CR_EXP" NUMBER(20,2), "TOTAL_CR_EXP" NUMBER(20,2), "LOSS_PRO_HELD" NUMBER(20,2), "INTR_ARREARS" NUMBER(20,2), "TOTAL_INV_EXP_IF" NUMBER(20,2), "TOTAL_EXP" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC6_PART_A
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC6_PART_A" ("CATEGORY_INVESTMENT_DOM_OPR" VARCHAR2(200), "HELD_MATURITY_BV" NUMBER(20,2), "AVAIL_FR_SALE_BV" NUMBER(20,2), "HELD_FR_TRADING_BV" NUMBER(20,2), "TOTAL_BV" NUMBER(20,2), "HELD_MATURITY_MV" NUMBER(20,2), "AVAIL_FR_SALE_MV" NUMBER(20,2), "HELD_FR_TRADING_MV" NUMBER(20,2), "TOTAL_MV" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC6_PART_B
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC6_PART_B" ("ITEM" VARCHAR2(200), "AMT_CR_QTR" NUMBER(20,2), "AMT_CR_YR" NUMBER(20,2), "TOTAL_CR_QTR" NUMBER(20,2), "TOTAL_CR_YR" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC6_PART_C
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC6_PART_C" ("CATEGORY" VARCHAR2(200), "ITEM" VARCHAR2(200), "TL_HLD_RATE" NUMBER(20,2), "TL_HLD_UNRATE" NUMBER(20,2), "TL_HLD_BRWR" NUMBER(20,2), "TL_HLD_NONBRWR" NUMBER(20,2), "AATPP_RATE" NUMBER(20,2), "AATPP_UNRATE" NUMBER(20,2), "TOTAL_NPA" NUMBER(20,2), "TOTAL_PRO_HELD" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC6_PART_C_2
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC6_PART_C_2" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC6_PART_D
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC6_PART_D" ("DESCRIPTION" VARCHAR2(100), "DOMESTIC" NUMBER(20,2), "OVERSEAS" NUMBER(20,2), "GLOBAL" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC7_EXP_CR
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC7_EXP_CR" ("DISBURSH_PRE_RUP_CR" NUMBER(20,2), "DISBURSH_PRE_PCFC" NUMBER(20,2), "DISBURSH_PRE_TOTAL" NUMBER(20,2), "DISBURSH_POST_RUP_CR" NUMBER(20,2), "DISBURSH_POST_EBR" NUMBER(20,2), "DISBURSH_POST_DEFER_PAYMENT" NUMBER(20,2), "DISBURSH_POST_OTR_GOVT_PAYMENT" NUMBER(20,2), "DISBURSH_POST_TOTAL" NUMBER(20,2), "DISBURSH_TOTAL" NUMBER(20,2), "BAL_OUT_PRE_RUP_CR" NUMBER(20,2), "BAL_OUT_PRE_PCFC" NUMBER(20,2), "BAL_OUT_PRE_TOTAL" NUMBER(20,2), "BAL_OUT_POST_RUP_CR" NUMBER(20,2), "BAL_OUT_POST_EBR" NUMBER(20,2), "BAL_OUT_POST_DEFER_PAYMENT" NUMBER(20,2), "BAL_OUT_POST_OTR_GOVT_PAYMENT" NUMBER(20,2), "BAL_OUT_POST_TOTAL" NUMBER(20,2), "BAL_OUT_TOTAL" NUMBER(20,2), "NO_GOLD_CARD_ISSUED" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC8_IND_BRKUP
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC8_IND_BRKUP" ("INDUSTRY_NAME" VARCHAR2(200), "TL_F_CR_EXP" NUMBER(20,2), "TL_NF_CR_EXP" NUMBER(20,2), "TL_F_AND_NF_CR__EXP" NUMBER(20,2), "TL_INV_EXP" NUMBER(20,2), "TL_EXP" NUMBER(20,2), "FUN_ADV_OUT" NUMBER(20,2), "OF_WCH_SEC_FUN_ADV_OUT" NUMBER(20,2), "NFFUN_ADV_OUT" NUMBER(20,2), "STD_FUN_ADV" NUMBER(20,2), "GROSS_NPA_BEG" NUMBER(20,2), "NEW_ACC_NPA_STD" NUMBER(20,2), "UPGRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPA_END" NUMBER(20,2), "SMA_0" NUMBER(20,2), "SMA_1" NUMBER(20,2), "SMA_2" NUMBER(20,2), "SUBSTANDARD_ADV" NUMBER(20,2), "DOUBT_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PRO_HELD" NUMBER(20,2), "CUM_WRITE_OFFS" NUMBER(20,2), "TECH_PRUD_WRITE_OFFS" NUMBER(20,2), "RESTRUCTURED_STAND_ADV" NUMBER(20,2), "TL_TERM_LOANS_SANCT" NUMBER(20,2), "TL_TERM_LOANS_DISBUR" NUMBER(20,2), "TL_BILLS_PURCHASED" NUMBER(20,2), "NET_LOANS_DISBURSED" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC8_INFRA_BRKUP
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC8_INFRA_BRKUP" ("INDUSTRY_NAME" VARCHAR2(200), "TL_F_CR_EXP" NUMBER(20,2), "TL_NF_CR_EXP" NUMBER(20,2), "TL_F_AND_NF_CR__EXP" NUMBER(20,2), "TL_INV_EXP" NUMBER(20,2), "TL_EXP" NUMBER(20,2), "FUN_ADV_OUT" NUMBER(20,2), "OF_WCH_SEC_FUN_ADV_OUT" NUMBER(20,2), "NFFUN_ADV_OUT" NUMBER(20,2), "STD_FUN_ADV" NUMBER(20,2), "GROSS_NPA_BEG" NUMBER(20,2), "NEW_ACC_NPA_STD" NUMBER(20,2), "UPGRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPA_END" NUMBER(20,2), "SMA_0" NUMBER(20,2), "SMA_1" NUMBER(20,2), "SMA_2" NUMBER(20,2), "SUBSTANDARD_ADV" NUMBER(20,2), "DOUBT_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PRO_HELD" NUMBER(20,2), "CUM_WRITE_OFFS" NUMBER(20,2), "TECH_PRUD_WRITE_OFFS" NUMBER(20,2), "RESTRUCTURED_STAND_ADV" NUMBER(20,2), "TL_TERM_LOANS_SANCT" NUMBER(20,2), "TL_TERM_LOANS_DISBUR" NUMBER(20,2), "TL_BILLS_PURCHASED" NUMBER(20,2), "NET_LOANS_DISBURSED" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC8_SEC_CREDIT
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC8_SEC_CREDIT" ("ITEM" VARCHAR2(200), "TL_F_CR_EXP" NUMBER(20,2), "TL_NF_CR_EXP" NUMBER(20,2), "TL_F_AND_NF_CR__EXP" NUMBER(20,2), "TL_INV_EXP" NUMBER(20,2), "TL_EXP" NUMBER(20,2), "FUN_ADV_OUT" NUMBER(20,2), "OF_WCH_SEC_FUN_ADV_OUT" NUMBER(20,2), "NFFUN_ADV_OUT" NUMBER(20,2), "STD_FUN_ADV" NUMBER(20,2), "GROSS_NPA_BEG" NUMBER(20,2), "NEW_ACC_NPA_STD" NUMBER(20,2), "UPGRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPA_END" NUMBER(20,2), "SMA_0" NUMBER(20,2), "SMA_1" NUMBER(20,2), "SMA_2" NUMBER(20,2), "SUBSTANDARD_ADV" NUMBER(20,2), "DOUBT_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PRO_HELD" NUMBER(20,2), "CUM_WRITE_OFFS" NUMBER(20,2), "TECH_PRUD_WRITE_OFFS" NUMBER(20,2), "RESTRUCTURED_STAND_ADV" NUMBER(20,2), "TL_TERM_LOANS_SANCT" NUMBER(20,2), "TL_TERM_LOANS_DISBUR" NUMBER(20,2), "TL_BILLS_PURCHASED" NUMBER(20,2), "NET_LOANS_DISBURSED" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC8_SEC_CREDIT_1
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC8_SEC_CREDIT_1" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC9_SENSEC_PARTA
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC9_SENSEC_PARTA" ("DESCRIPTION" VARCHAR2(200), "EXPOSURE_DOM" NUMBER(20,2), "GROSS_AMT_OS_DOM" NUMBER(20,2), "OF_WHICH_IMPAIRED_DOM" NUMBER(20,2), "EXPOSURE_OVE" NUMBER(20,2), "GROSS_AMT_OS_OVE" NUMBER(20,2), "OF_WHICH_IMPAIRED_OVE" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE, "TYPE_ID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC9_SENSEC_PARTA_bkup
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC9_SENSEC_PARTA_bkup" ("DESCRIPTION" VARCHAR2(200), "EXPOSURE_DOM" NUMBER(20,2), "GROSS_AMT_OS_DOM" NUMBER(20,2), "OF_WHICH_IMPAIRED_DOM" NUMBER(20,2), "EXPOSURE_OVE" NUMBER(20,2), "GROSS_AMT_OS_OVE" NUMBER(20,2), "OF_WHICH_IMPAIRED_OVE" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE, "TYPE_ID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC9_SENSEC_PARTB
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC9_SENSEC_PARTB" ("DESCRIPTION" VARCHAR2(200), "TOT_EXPO_DOM" NUMBER(20,2), "AMT_OS_FUNDED_DOM" NUMBER(20,2), "RESTRU_STD_DOM" NUMBER(20,2), "IMPAIRED_DOM" NUMBER(20,2), "SLIPPAGE_DOM" NUMBER(20,2), "TOT_EXPO_OVE" NUMBER(20,2), "AMT_OS_FUNDED_OVE" NUMBER(20,2), "RESTRU_STD_OVE" NUMBER(20,2), "IMPAIRED_OVE" NUMBER(20,2), "SLIPPAGE_OVE" NUMBER(20,2), "CODE" NUMBER(20), "TYPEID" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC_12_MISC
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC_12_MISC" ("ITEM" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC_12_MISC_T2
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC_12_MISC_T2" ("CATEGORY" VARCHAR2(200), "IND_MICRO" NUMBER(20), "IND_SMALL" NUMBER(20), "IND_MEDIUM" NUMBER(20), "SER_MICRO" NUMBER(20), "SER_SMALL" NUMBER(20), "SER_MEDIUM" NUMBER(20), "TOT_MICRO" NUMBER(20), "TOT_SMALL" NUMBER(20), "TOT_MEDIUM" NUMBER(20), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC_12_MISC_T3
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC_12_MISC_T3" ("DESCRIPTION" VARCHAR2(200), "AMT" NUMBER(20,2), "MIN_INT" NUMBER(20,4), "MAX_INT" NUMBER(20,4), "WEGHT_AVG_INT" NUMBER(20,4), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SEC_12_MISC_T4
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SEC_12_MISC_T4" ("DESCRIPTION" VARCHAR2(200), "GROSS_ADV" NUMBER(20,2), "GROSS_NPA" NUMBER(20,2), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RAQ_Q_SIGNATORY
--------------------------------------------------------

  CREATE TABLE "CIMS_RAQ_Q_SIGNATORY" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RBS_Q_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_RBS_Q_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RBS_Q_NET_OVE_INV
--------------------------------------------------------

  CREATE TABLE "CIMS_RBS_Q_NET_OVE_INV" ("DESCRIPTION" VARCHAR2(200), "VALUE" NUMBER(20,4), "CODE" VARCHAR2(100), "RDATE" DATE, "SRNO" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_RBS_Q_NONSLR_PART_A
--------------------------------------------------------

  CREATE TABLE "CIMS_RBS_Q_NONSLR_PART_A" ("SR_NO" VARCHAR2(100), "EXTERNAL_RATING" VARCHAR2(1000), "AMOUNT" NUMBER(20,2), "REMARKS" VARCHAR2(1000), "TRANSATION_ID" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RBS_Q_NONSLR_PART_B
--------------------------------------------------------

  CREATE TABLE "CIMS_RBS_Q_NONSLR_PART_B" ("SR_NO" VARCHAR2(100), "INTERNAL_RATING" VARCHAR2(1000), "AMOUNT" NUMBER, "REMARKS" VARCHAR2(1000), "TRANSACTION_ID" VARCHAR2(100), "CODE" NUMBER(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RBS_Q_RATING_WISE_MEMO
--------------------------------------------------------

  CREATE TABLE "CIMS_RBS_Q_RATING_WISE_MEMO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RBS_Q_RATING_WISE_STDADV
--------------------------------------------------------

  CREATE TABLE "CIMS_RBS_Q_RATING_WISE_STDADV" ("Sr_No" VARCHAR2(10), "INT_RATING" VARCHAR2(150), "TYPE_OF_FCLT" VARCHAR2(150), "RUP_ADV_NO_ACC" NUMBER, "RUP_ADV_AMT_ADV" NUMBER, "RUP_ADV_ROI_MIN_RATE" NUMBER, "RUP_ADV_ROI_MAX_RATE" NUMBER, "RUP_ADV_ROI_WTD_AVG" NUMBER, "FC_ADV_NO_ACC" NUMBER, "FC_ADV_AMT_ADV" NUMBER, "FC_ADV_ROI_MIN_RATE" NUMBER, "FC_ADV_ROI_MAX_RATE" NUMBER, "FC_ADV_ROI_WTD_AVG" NUMBER, "REMARK" VARCHAR2(200), "TRANSATION_ID" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RBS_Q_SEC4_CR_CARD_BSE
--------------------------------------------------------

  CREATE TABLE "CIMS_RBS_Q_SEC4_CR_CARD_BSE" ("CATEGORY" VARCHAR2(500), "DOM_DOMSTIC_CARDS" NUMBER(20,2), "DOM_INTERNL_CARDS" NUMBER(20,2), "DOM_TOTAL" NUMBER(20,2), "OVER_OPER" NUMBER(20,2), "GLOBL_OPER" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RBS_Q_SEC5_HUSING_FIN
--------------------------------------------------------

  CREATE TABLE "CIMS_RBS_Q_SEC5_HUSING_FIN" ("PARTICULARS" VARCHAR2(1000), "AMOUNT_OF_DIRECT_HF" NUMBER(20,2), "AMOUNT_OF_INDIRECT_HF" NUMBER(20,2), "NHB" NUMBER(20,2), "HUDCO" NUMBER(20,2), "MBS" NUMBER(20,2), "TOTAL" NUMBER(20,2), "GRAND_TOTAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RBS_Q_SECURITIZATION
--------------------------------------------------------

  CREATE TABLE "CIMS_RBS_Q_SECURITIZATION" ("LOAN_SALES_SECURITIZATION" VARCHAR2(500), "DOM_AMOUNT" VARCHAR2(500), "DOM_PROVISION_HELD" NUMBER, "DOM_GAIN_LOSS" NUMBER, "DOM_RETAIN_INTEREST" NUMBER, "OVS_AMOUNT" VARCHAR2(500), "OVS_PROVISION_HELD" NUMBER, "OVS_GAIN_LOSS" NUMBER, "OVS_RETAIN_INTEREST" NUMBER, "REMARKS" VARCHAR2(500), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RBS_Q_SIGNATORY
--------------------------------------------------------

  CREATE TABLE "CIMS_RBS_Q_SIGNATORY" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA1_Q_CAPITAL_BASE
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA1_Q_CAPITAL_BASE" ("SRNO" NUMBER(20,2), "DESCRIPTION" VARCHAR2(200), "CUR_Q_AMOUNT" NUMBER(20,4), "PREV_Q_AMOUNT" NUMBER(20,4), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA1_Q_COMPU_CAP_BASE_IB
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA1_Q_COMPU_CAP_BASE_IB" ("SRNO" NUMBER(20,2), "DESCRIPTION" VARCHAR2(200), "AMOUNT" NUMBER(20,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA1_Q_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA1_Q_GEN_INFO" ("SRNO" NUMBER(20,2), "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA1_Q_GLOBAL_POS_END_Q
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA1_Q_GLOBAL_POS_END_Q" ("SRNO" NUMBER(20,2), "DESCRIPTION" VARCHAR2(200), "AMOUNT" NUMBER(20,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA1_Q_RWAE_SEC_A
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA1_Q_RWAE_SEC_A" ("SRNO" NUMBER(20,2), "ASSET_ITEM" VARCHAR2(200), "TTL_BOOK_VAL" NUMBER(20,4), "HLD_UNDER_BANK_BOOK" NUMBER(20,4), "MARGIN_PROVI" NUMBER(20,4), "BOOK_VAL_NET" NUMBER(20,4), "RISK_WEIGHT_PERC" NUMBER(20,4), "RISK_ADJUSTED_VAL" NUMBER(20,4), "CODE" VARCHAR2(100), "SERVICE_TYPE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA1_Q_RWAE_SEC_B
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA1_Q_RWAE_SEC_B" ("SRNO" NUMBER(20,2), "OBS_ITEM" VARCHAR2(200), "CLIENT_OBLIGANT" VARCHAR2(200), "TTL_BOOK_EXPO" NUMBER(20,4), "MARGIN_PROVI" NUMBER(20,4), "BOOK_EXPO_NET" NUMBER(20,4), "CCF_CONTING" NUMBER(20,4), "RW_OBLIANT" NUMBER(20,4), "RAV_EXPO" NUMBER(20,4), "CODE" VARCHAR2(100), "SERVICE_TYPE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA1_Q_RWAE_SEC_C
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA1_Q_RWAE_SEC_C" ("SRNO" NUMBER(20,2), "ITEM" VARCHAR2(200), "POT_FUTUR_CREDIT_EXPO_FACT" NUMBER(20,4), "COUNTER_PARTY" VARCHAR2(200), "NOTIONAL_PRIN_AMT" NUMBER(20,4), "POTENTIAL_EXPO" NUMBER(20,4), "REPLACE_COST" NUMBER(20,4), "CURR_EXPO" NUMBER(20,4), "CRED_EQUIV_AMT" NUMBER(20,4), "RISK_WEIGHT_PERC" NUMBER(20,4), "RISK_ADJUSTED_VAL" NUMBER(20,4), "CODE" VARCHAR2(100), "SERVICE_TYPE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA1_Q_RWAE_SEC_D
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA1_Q_RWAE_SEC_D" ("SRNO" NUMBER(20,2), "DESCRIPTION" VARCHAR2(200), "AMOUNT" NUMBER(20,2), "CODE" VARCHAR2(100), "SERVICE_TYPE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA1_Q_SIGNATORY
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA1_Q_SIGNATORY" ("SRNO" NUMBER(20,2), "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA1_Q_UNDISCLOSED_RESERV
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA1_Q_UNDISCLOSED_RESERV" ("SRNO" NUMBER(20,2), "AMOUNT_NAME" VARCHAR2(200), "AMOUNT" NUMBER(20,2), "GROUP_NAME" VARCHAR2(200), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_AGG_CAP_FOR_MKT_RISK
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_AGG_CAP_FOR_MKT_RISK" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "VAL" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_CCR_AS_BORROWER
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_CCR_AS_BORROWER" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CNTR_PARTY" VARCHAR2(500), "RATING" VARCHAR2(200), "CAR" VARCHAR2(200), "EXP_AMT" NUMBER(20,2), "CCF" VARCHAR2(20), "CEA" NUMBER(20,2), "H_ADJ_AMT" NUMBER(20,2), "CSL" NUMBER(20,2), "H_ADJ_COL" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_CCR_AS_LENDER
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_CCR_AS_LENDER" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CNTR_PARTY" VARCHAR2(200), "RATING" VARCHAR2(200), "CAR" VARCHAR2(200), "EXP_AMT" NUMBER(20,2), "H_ADJ_AMT" NUMBER(20,2), "CCL" NUMBER(20,2), "H_ADJ_COL" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_CCR_CDS
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_CCR_CDS" ("SRNO" NUMBER, "DECR" VARCHAR2(500), "CP" VARCHAR2(200), "NA_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "AMT_CP_CR" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_CR_MR_OFF_BS
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_CR_MR_OFF_BS" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CP_PURP_TOA" VARCHAR2(500), "RATING" VARCHAR2(200), "CAR" VARCHAR2(200), "NPA" NUMBER(20,4), "P_EXP" NUMBER(20,4), "REPL_COST" NUMBER(20,4), "CURR_EXP" NUMBER(20,4), "CEA" NUMBER(20,4), "ADJ_VAL_CR" NUMBER(20,4), "NET_EXP" NUMBER(20,4), "RW" VARCHAR2(20), "RAV" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_CR_NMR_OFF_BS
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_CR_NMR_OFF_BS" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "OBLI_PURP_TOA" VARCHAR2(500), "RATING" VARCHAR2(200), "CAR" VARCHAR2(200), "EXP_AMT" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_CR_NONQCCPS_TBL_1
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_CR_NONQCCPS_TBL_1" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CCF" VARCHAR2(20), "AMT_EXP" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_CR_NONQCCPS_TBL_2
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_CR_NONQCCPS_TBL_2" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "POT_CR_EXP" VARCHAR2(20), "NPE" NUMBER(20,2), "POT_EXP" NUMBER(20,2), "RE_COST" NUMBER(20,2), "CURR_EXP" NUMBER(20,2), "CRE_EQU" NUMBER(20,2), "ADJ_VAL" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_CR_NONQCCPS_TBL_2_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_CR_NONQCCPS_TBL_2_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "POT_CR_EXP" VARCHAR2(20), "NPE" NUMBER(20,2), "POT_EXP" NUMBER(20,2), "RE_COST" NUMBER(20,2), "CURR_EXP" NUMBER(20,2), "CRE_EQU" NUMBER(20,2), "ADJ_VAL" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_CR_OFF_BS_RESEC
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_CR_OFF_BS_RESEC" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "CCF" VARCHAR2(20), "EXP_AMT" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_CR_OFF_BS_RSEC_ADITM
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_CR_OFF_BS_RSEC_ADITM" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "RATING" VARCHAR2(200), "CCF" VARCHAR2(20), "EXP_AMT" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_CR_OFF_BS_SEC
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_CR_OFF_BS_SEC" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "CCF" VARCHAR2(20), "EXP_AMT" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_CR_OFF_BS_SEC_ADITM
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_CR_OFF_BS_SEC_ADITM" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "RATING" VARCHAR2(200), "CCF" VARCHAR2(20), "EXP_AMT" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_CR_ONBS_EXCLSEC_S_AD
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_CR_ONBS_EXCLSEC_S_AD" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "RATING" VARCHAR2(200), "EXP_AMT" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_CR_ON_BS_EXCL_SEC_S
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_CR_ON_BS_EXCL_SEC_S" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "EXP_AMT" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_CR_ON_BS_RESEC
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_CR_ON_BS_RESEC" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "EXP_AMT" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_CR_ON_BS_SEC
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_CR_ON_BS_SEC" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "EXP_AMT" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_CR_QCCPS_TBL_1
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_CR_QCCPS_TBL_1" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CCF" VARCHAR2(20), "AMT_EXP" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "QCCP_TYPE" VARCHAR2(500), "QCCP_NAME" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_CR_QCCPS_TBL_1_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_CR_QCCPS_TBL_1_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CCF" VARCHAR2(20), "AMT_EXP" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "QCCP_TYPE" VARCHAR2(500), "QCCP_NAME" VARCHAR2(200), "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_CR_QCCPS_TBL_2
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_CR_QCCPS_TBL_2" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "VAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "QCCP_TYPE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_CR_QCCPS_TBL_3
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_CR_QCCPS_TBL_3" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "POT_CR_EXP" VARCHAR2(200), "NPE" NUMBER(20,2), "POT_EXP" NUMBER(20,2), "RE_COST" NUMBER(20,2), "CURR_EXP" NUMBER(20,2), "CRE_EQU" NUMBER(20,2), "ADJ_VAL" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "QCCP_TYPE" VARCHAR2(500), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_CR_QCCPS_TBL_3_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_CR_QCCPS_TBL_3_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "POT_CR_EXP" VARCHAR2(200), "NPE" NUMBER(20,2), "POT_EXP" NUMBER(20,2), "RE_COST" NUMBER(20,2), "CURR_EXP" NUMBER(20,2), "CRE_EQU" NUMBER(20,2), "ADJ_VAL" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "QCCP_TYPE" VARCHAR2(500), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_AG_CAP_FOR_MKT_RSK
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_AG_CAP_FOR_MKT_RSK" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "VAL" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_AG_CAP_FOR_MKT_RSK_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_AG_CAP_FOR_MKT_RSK_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "VAL" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CCR_AS_BORROWER
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CCR_AS_BORROWER" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CNTR_PARTY" VARCHAR2(500), "RATING" VARCHAR2(200), "CAR" VARCHAR2(200), "EXP_AMT" NUMBER(20,2), "CCF" VARCHAR2(20), "CEA" NUMBER(20,2), "H_ADJ_AMT" NUMBER(20,2), "CSL" NUMBER(20,2), "H_ADJ_COL" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CCR_AS_BORROWER_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CCR_AS_BORROWER_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CNTR_PARTY" VARCHAR2(500), "RATING" VARCHAR2(200), "CAR" VARCHAR2(200), "EXP_AMT" NUMBER(20,2), "CCF" VARCHAR2(20), "CEA" NUMBER(20,2), "H_ADJ_AMT" NUMBER(20,2), "CSL" NUMBER(20,2), "H_ADJ_COL" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CCR_AS_LENDER
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CCR_AS_LENDER" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CNTR_PARTY" VARCHAR2(200), "RATING" VARCHAR2(200), "CAR" VARCHAR2(200), "EXP_AMT" NUMBER(20,2), "H_ADJ_AMT" NUMBER(20,2), "CCL" NUMBER(20,2), "H_ADJ_COL" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CCR_AS_LENDER_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CCR_AS_LENDER_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CNTR_PARTY" VARCHAR2(200), "RATING" VARCHAR2(200), "CAR" VARCHAR2(200), "EXP_AMT" NUMBER(20,2), "H_ADJ_AMT" NUMBER(20,2), "CCL" NUMBER(20,2), "H_ADJ_COL" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CCR_CDS
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CCR_CDS" ("SRNO" NUMBER, "DECR" VARCHAR2(500), "CP" VARCHAR2(200), "NA_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "AMT_CP_CR" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CCR_CDS_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CCR_CDS_HIST" ("SRNO" NUMBER, "DECR" VARCHAR2(500), "CP" VARCHAR2(200), "NA_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "AMT_CP_CR" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_MR_OFF_BS
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_MR_OFF_BS" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CP_PURP_TOA" VARCHAR2(500), "RATING" VARCHAR2(200), "CAR" VARCHAR2(200), "NPA" NUMBER(20,4), "P_EXP" NUMBER(20,4), "REPL_COST" NUMBER(20,4), "CURR_EXP" NUMBER(20,4), "CEA" NUMBER(20,4), "ADJ_VAL_CR" NUMBER(20,4), "NET_EXP" NUMBER(20,4), "RW" VARCHAR2(20), "RAV" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_MR_OFF_BS_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_MR_OFF_BS_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CP_PURP_TOA" VARCHAR2(500), "RATING" VARCHAR2(200), "CAR" VARCHAR2(200), "NPA" NUMBER(20,4), "P_EXP" NUMBER(20,4), "REPL_COST" NUMBER(20,4), "CURR_EXP" NUMBER(20,4), "CEA" NUMBER(20,4), "ADJ_VAL_CR" NUMBER(20,4), "NET_EXP" NUMBER(20,4), "RW" VARCHAR2(20), "RAV" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_NMR_OFF_BS
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_NMR_OFF_BS" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "OBLI_PURP_TOA" VARCHAR2(500), "RATING" VARCHAR2(200), "CAR" VARCHAR2(200), "EXP_AMT" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_NMR_OFF_BS_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_NMR_OFF_BS_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "OBLI_PURP_TOA" VARCHAR2(500), "RATING" VARCHAR2(200), "CAR" VARCHAR2(200), "EXP_AMT" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_NONQCCPS_TBL_1
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_NONQCCPS_TBL_1" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CCF" VARCHAR2(20), "AMT_EXP" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_NONQCCPS_TBL_1_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_NONQCCPS_TBL_1_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CCF" VARCHAR2(20), "AMT_EXP" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_NONQCCPS_TBL_2
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_NONQCCPS_TBL_2" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "POT_CR_EXP" VARCHAR2(20), "NPE" NUMBER(20,2), "POT_EXP" NUMBER(20,2), "RE_COST" NUMBER(20,2), "CURR_EXP" NUMBER(20,2), "CRE_EQU" NUMBER(20,2), "ADJ_VAL" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_NONQCCPS_TBL_2_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_NONQCCPS_TBL_2_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "POT_CR_EXP" VARCHAR2(20), "NPE" NUMBER(20,2), "POT_EXP" NUMBER(20,2), "RE_COST" NUMBER(20,2), "CURR_EXP" NUMBER(20,2), "CRE_EQU" NUMBER(20,2), "ADJ_VAL" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_OFBS_RSEC_ADITM
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_OFBS_RSEC_ADITM" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "RATING" VARCHAR2(200), "CCF" VARCHAR2(20), "EXP_AMT" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_OFBS_RSEC_ADITM_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_OFBS_RSEC_ADITM_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "RATING" VARCHAR2(200), "CCF" VARCHAR2(20), "EXP_AMT" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_OFFBS_SEC_ADITM
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_OFFBS_SEC_ADITM" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "RATING" VARCHAR2(200), "CCF" VARCHAR2(20), "EXP_AMT" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_OFFBS_SEC_ADITM_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_OFFBS_SEC_ADITM_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "RATING" VARCHAR2(200), "CCF" VARCHAR2(20), "EXP_AMT" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_OFF_BS_RESEC
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_OFF_BS_RESEC" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "CCF" VARCHAR2(20), "EXP_AMT" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_OFF_BS_RESEC_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_OFF_BS_RESEC_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "CCF" VARCHAR2(20), "EXP_AMT" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_OFF_BS_SEC
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_OFF_BS_SEC" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "CCF" VARCHAR2(20), "EXP_AMT" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_OFF_BS_SEC_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_OFF_BS_SEC_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "CCF" VARCHAR2(20), "EXP_AMT" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_ONBS_EXCLSEC_AD
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_ONBS_EXCLSEC_AD" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "RATING" VARCHAR2(200), "EXP_AMT" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_ONBS_EXCLSEC_AD_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_ONBS_EXCLSEC_AD_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "RATING" VARCHAR2(200), "EXP_AMT" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_ON_BS_EXCL_SEC
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_ON_BS_EXCL_SEC" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "EXP_AMT" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_ON_BS_EXCL_SEC_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_ON_BS_EXCL_SEC_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "EXP_AMT" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_ON_BS_RESEC
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_ON_BS_RESEC" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "EXP_AMT" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_ON_BS_RESEC_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_ON_BS_RESEC_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "EXP_AMT" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_ON_BS_SEC
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_ON_BS_SEC" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "EXP_AMT" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_ON_BS_SEC_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_ON_BS_SEC_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "EXP_AMT" NUMBER(20,2), "ADJ_VAL_CR" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_QCCPS_TBL_1
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_QCCPS_TBL_1" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CCF" VARCHAR2(20), "AMT_EXP" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "QCCP_TYPE" VARCHAR2(500), "QCCP_NAME" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_QCCPS_TBL_1_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_QCCPS_TBL_1_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CCF" VARCHAR2(20), "AMT_EXP" NUMBER(20,2), "CEA" NUMBER(20,2), "ADJ_VAL" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "QCCP_TYPE" VARCHAR2(500), "QCCP_NAME" VARCHAR2(200), "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_QCCPS_TBL_2
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_QCCPS_TBL_2" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "VAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "QCCP_TYPE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_QCCPS_TBL_2_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_QCCPS_TBL_2_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "VAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "QCCP_TYPE" VARCHAR2(20), "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_QCCPS_TBL_3
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_QCCPS_TBL_3" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "POT_CR_EXP" VARCHAR2(200), "NPE" NUMBER(20,2), "POT_EXP" NUMBER(20,2), "RE_COST" NUMBER(20,2), "CURR_EXP" NUMBER(20,2), "CRE_EQU" NUMBER(20,2), "ADJ_VAL" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "QCCP_TYPE" VARCHAR2(500), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_CR_QCCPS_TBL_3_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_CR_QCCPS_TBL_3_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "POT_CR_EXP" VARCHAR2(200), "NPE" NUMBER(20,2), "POT_EXP" NUMBER(20,2), "RE_COST" NUMBER(20,2), "CURR_EXP" NUMBER(20,2), "CRE_EQU" NUMBER(20,2), "ADJ_VAL" NUMBER(20,2), "NET_EXP" NUMBER(20,2), "QCCP_TYPE" VARCHAR2(500), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_FAILED_TRN_OFF_BS
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_FAILED_TRN_OFF_BS" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "CP_CL" VARCHAR2(200), "RATING" VARCHAR2(200), "CAR" VARCHAR2(200), "AGR_SET" NUMBER(20,2), "CMP" NUMBER(20,2), "CE" NUMBER(20,2), "RM" VARCHAR2(20), "AMT_CAP_CHRG" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_FAILED_TRN_OFF_BS_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_FAILED_TRN_OFF_BS_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "CP_CL" VARCHAR2(200), "RATING" VARCHAR2(200), "CAR" VARCHAR2(200), "AGR_SET" NUMBER(20,2), "CMP" NUMBER(20,2), "CE" NUMBER(20,2), "RM" VARCHAR2(20), "AMT_CAP_CHRG" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_FAILED_TRN_ON_BS
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_FAILED_TRN_ON_BS" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "CP_CL" VARCHAR2(200), "RATING" VARCHAR2(200), "CAR" VARCHAR2(200), "AMT_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_FAILED_TRN_ON_BS_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_FAILED_TRN_ON_BS_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "CP_CL" VARCHAR2(200), "RATING" VARCHAR2(200), "CAR" VARCHAR2(200), "AMT_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_GENERAL_INFORMTION
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_GENERAL_INFORMTION" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(500), "VAL" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_GENERAL_INFORMTION_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_GENERAL_INFORMTION_HIST" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(500), "VAL" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_MKTRSK_ALT_CAP_AFS
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_MKTRSK_ALT_CAP_AFS" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CAP_CHR_PERC" VARCHAR2(20), "EXP_AMT" NUMBER(20,4), "AMT_CAP_CHR" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_MKTRSK_ALT_CAP_AFS_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_MKTRSK_ALT_CAP_AFS_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CAP_CHR_PERC" VARCHAR2(20), "EXP_AMT" NUMBER(20,4), "AMT_CAP_CHR" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE, "TYPEID" NUMBER, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_MKTRSK_SPECFIC_AFS
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_MKTRSK_SPECFIC_AFS" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CAP_CHR_PERC" VARCHAR2(20), "EXP_AMT" NUMBER(20,4), "AMT_CAP_CHR" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_MKTRSK_SPECFIC_AFS_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_MKTRSK_SPECFIC_AFS_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CAP_CHR_PERC" VARCHAR2(20), "EXP_AMT" NUMBER(20,4), "AMT_CAP_CHR" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE, "TYPEID" NUMBER, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_MKTRSK_SPECFIC_CDS
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_MKTRSK_SPECFIC_CDS" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CAP_CHR_PERC" VARCHAR2(20), "EXP_AMT" NUMBER(20,4), "AMT_CAP_CHR" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_MKTRSK_SPECFIC_CDS_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_MKTRSK_SPECFIC_CDS_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CAP_CHR_PERC" VARCHAR2(20), "EXP_AMT" NUMBER(20,4), "AMT_CAP_CHR" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_MKTRSK_SPECFIC_HFT
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_MKTRSK_SPECFIC_HFT" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CAP_CHR_PERC" VARCHAR2(20), "EXP_AMT" NUMBER(20,4), "AMT_CAP_CHR" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_MKTRSK_SPECFIC_HFT_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_MKTRSK_SPECFIC_HFT_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CAP_CHR_PERC" VARCHAR2(20), "EXP_AMT" NUMBER(20,4), "AMT_CAP_CHR" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_OPERATIONAL_RISK
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_OPERATIONAL_RISK" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "BETA_FACTOR_PERCENT_PRE_FY" VARCHAR2(20), "GI_1YR_GI" NUMBER(20,2), "GI_2YR_GII" NUMBER(20,2), "GI_3YR_GIII" NUMBER(20,2), "CC_1YR_CCI" NUMBER(20,2), "CC_2YR_CCII" NUMBER(20,2), "CC_3YR_CCIII" NUMBER(20,2), "QUARTER_CQ_OR_PQ" VARCHAR2(500), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_OPERATIONAL_RISK_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_OPERATIONAL_RISK_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "BETA_FACTOR_PERCENT_PRE_FY" VARCHAR2(20), "GI_1YR_GI" NUMBER(20,2), "GI_2YR_GII" NUMBER(20,2), "GI_3YR_GIII" NUMBER(20,2), "CC_1YR_CCI" NUMBER(20,2), "CC_2YR_CCII" NUMBER(20,2), "CC_3YR_CCIII" NUMBER(20,2), "QUARTER_CQ_OR_PQ" VARCHAR2(500), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_RGULTRY_CAP_BASEL3
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_RGULTRY_CAP_BASEL3" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "ELE_AMT" NUMBER(20,2), "REG_ADJ_AMT" NUMBER(20,2), "TOT_REG_ADJ" NUMBER(20,2), "REMARKS" NUMBER, "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_RGULTRY_CAP_BASEL3_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_RGULTRY_CAP_BASEL3_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "ELE_AMT" NUMBER(20,2), "REG_ADJ_AMT" NUMBER(20,2), "TOT_REG_ADJ" NUMBER(20,2), "REMARKS" NUMBER, "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_RWA
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_RWA" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "VAL" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_C_RWA_HIST
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_C_RWA_HIST" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "VAL" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE, "APPROVED_DATA" NUMBER, "UPDATED_DATE" TIMESTAMP(6), "APPROVED_BY" VARCHAR2(200), "APPOVEDDATETIME" DATE, "UPLOADEDBY" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_FAILED_TRN_OFF_BS
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_FAILED_TRN_OFF_BS" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "CP_CL" VARCHAR2(200), "RATING" VARCHAR2(200), "CAR" VARCHAR2(200), "AGR_SET" NUMBER(20,2), "CMP" NUMBER(20,2), "CE" NUMBER(20,2), "RM" VARCHAR2(20), "AMT_CAP_CHRG" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_FAILED_TRN_ON_BS
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_FAILED_TRN_ON_BS" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "CP_CL" VARCHAR2(200), "RATING" VARCHAR2(200), "CAR" VARCHAR2(200), "AMT_EXP" NUMBER(20,2), "RW" VARCHAR2(20), "RAV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_GENERAL_INFORMATION
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_GENERAL_INFORMATION" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(500), "VAL" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_MKTRISK_ALT_CAP_AFS
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_MKTRISK_ALT_CAP_AFS" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CAP_CHR_PERC" VARCHAR2(20), "EXP_AMT" NUMBER(20,4), "AMT_CAP_CHR" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_MKTRISK_SPECIFIC_AFS
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_MKTRISK_SPECIFIC_AFS" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CAP_CHR_PERC" VARCHAR2(20), "EXP_AMT" NUMBER(20,4), "AMT_CAP_CHR" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE, "TYPEID" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_MKTRISK_SPECIFIC_CDS
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_MKTRISK_SPECIFIC_CDS" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CAP_CHR_PERC" VARCHAR2(20), "EXP_AMT" NUMBER(20,4), "AMT_CAP_CHR" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_MKTRISK_SPECIFIC_HFT
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_MKTRISK_SPECIFIC_HFT" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "CAP_CHR_PERC" VARCHAR2(20), "EXP_AMT" NUMBER(20,4), "AMT_CAP_CHR" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_OPERATIONAL_RISK
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_OPERATIONAL_RISK" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "BETA_FACTOR_PERCENT_PRE_FY" VARCHAR2(20), "GI_1YR_GI" NUMBER(20,2), "GI_2YR_GII" NUMBER(20,2), "GI_3YR_GIII" NUMBER(20,2), "CC_1YR_CCI" NUMBER(20,2), "CC_2YR_CCII" NUMBER(20,2), "CC_3YR_CCIII" NUMBER(20,2), "QUARTER_CQ_OR_PQ" VARCHAR2(500), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_RGULATORY_CAP_BASEL3
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_RGULATORY_CAP_BASEL3" ("SRNO" NUMBER, "DESCR" VARCHAR2(1000), "ELE_AMT" NUMBER(20,2), "REG_ADJ_AMT" NUMBER(20,2), "TOT_REG_ADJ" NUMBER(20,2), "REMARKS" NUMBER, "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCA3_RWA
--------------------------------------------------------

  CREATE TABLE "CIMS_RCA3_RWA" ("SRNO" NUMBER, "DESCR" VARCHAR2(500), "VAL" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCL_Q_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_RCL_Q_GEN_INFO" ("RDATE" DATE, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table CIMS_RCL_Q_SECA
--------------------------------------------------------

  CREATE TABLE "CIMS_RCL_Q_SECA" ("SR_NO" NUMBER, "BANK_NAME" VARCHAR2(200), "BNK_EQTY_AMT" NUMBER(20), "HLD_EQTY_PER" NUMBER(20,2), "EXPOSUR_TYPE" VARCHAR2(100), "EXPOSURE_AMT" NUMBER(20,2), "OUTSTAND_AMT" NUMBER(20,2), "ASST_CLASIFC" VARCHAR2(100), "PROVISION" NUMBER(20,2), "TRANS_ID" VARCHAR2(60), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCL_Q_SECB
--------------------------------------------------------

  CREATE TABLE "CIMS_RCL_Q_SECB" ("SR_NO" NUMBER(20,2), "SHRLD_NAME" VARCHAR2(300), "INT_NATURE" VARCHAR2(300), "EXP_TYPE" VARCHAR2(300), "EXP_AMT" NUMBER(20,2), "TRM_CRDIT_EXP" NUMBER, "VALUE_SEC_COLL" NUMBER(20,2), "ASSET_CLASIF" VARCHAR2(300), "PROVI" NUMBER(20,2), "TRANS_ID" VARCHAR2(60), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCL_Q_SECC_A
--------------------------------------------------------

  CREATE TABLE "CIMS_RCL_Q_SECC_A" ("SR_NO" NUMBER, "NAME_DIR" VARCHAR2(300), "EXP_TYPE" VARCHAR2(300), "EXP_AMT" NUMBER(20,2), "TRM_CRDIT_EXP" NUMBER(20,2), "VALUE_SEC_COLL" NUMBER, "ASSET_CLASIF" VARCHAR2(300), "PROVI" NUMBER(20,2), "TRANS_ID" VARCHAR2(60), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RCL_Q_SECC_B
--------------------------------------------------------

  CREATE TABLE "CIMS_RCL_Q_SECC_B" ("SR_NO" NUMBER, "NAME_ASS_DIR" VARCHAR2(300), "NAME_INT_DIR" VARCHAR2(300), "INT_NATUR" VARCHAR2(200), "EXP_TYPE" VARCHAR2(300), "EXP_AMT" NUMBER(20,2), "TRM_CRDIT" NUMBER(20,2), "VALUE_SEC_COLL" NUMBER(20,2), "ASSET_CLASIF" VARCHAR2(300), "PROVI" NUMBER(20,2), "TRANS_ID" VARCHAR2(60), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RDA_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_RDA_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RDA_MAIN
--------------------------------------------------------

  CREATE TABLE "CIMS_RDA_MAIN" ("EXCHANGE_HUS" VARCHAR2(200), "COUNTRY" VARCHAR2(100), "INFLOW_FR_CR_USD" NUMBER(20,2), "INFLOW_RUPEE_EQU" NUMBER(20,2), "OUTFLOW_FR_CR_USD" NUMBER(20,2), "OUTFLOW_RUPEE_EQU" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RDA_SIGNATORY
--------------------------------------------------------

  CREATE TABLE "CIMS_RDA_SIGNATORY" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RDB_DEFAULT_BORROWERS
--------------------------------------------------------

  CREATE TABLE "CIMS_RDB_DEFAULT_BORROWERS" ("SR_NO" NUMBER, "BORROWER_PAN" VARCHAR2(200), "BORROWER_NAME" VARCHAR2(100), "WHETHER_PROJECT_FINANCE" VARCHAR2(10), "DATE_DEFAULT" VARCHAR2(100), "REASON_FOR_CREDIT_EVENT" VARCHAR2(250), "FUND_AMT_OUTSTAND" NUMBER(20,2), "NON_FUND_AMT_OUTSTAND" NUMBER(20,2), "TOTAL_AMT_OUTSTAND" NUMBER(20,2), "REMARKS" VARCHAR2(200), "TRANSACTION_ID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RDB_DEFAULT_BORROWERS_BACKUP
--------------------------------------------------------

  CREATE TABLE "CIMS_RDB_DEFAULT_BORROWERS_BACKUP" ("SR_NO" NUMBER, "BORROWER_PAN" VARCHAR2(200), "BORROWER_NAME" VARCHAR2(100), "DATE_DEFAULT" VARCHAR2(100), "FUND_AMT_OUTSTAND" NUMBER(20,2), "NON_FUND_AMT_OUTSTAND" NUMBER(20,2), "TOTAL_AMT_OUTSTAND" NUMBER(20,2), "REMARKS" VARCHAR2(200), "TRANSACTION_ID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RDB_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_RDB_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RDB_OUT_DEFAULT
--------------------------------------------------------

  CREATE TABLE "CIMS_RDB_OUT_DEFAULT" ("SR_NO" NUMBER, "BORROWER_PAN" VARCHAR2(200), "BORROWER_NAME" VARCHAR2(100), "WHETHER_PROJECT_FINANCE" VARCHAR2(10), "DT_MOVING_OUT_DEFAULT" VARCHAR2(100), "FUND_AMT_OUTSTAND" NUMBER(20,2), "NON_FUND_AMT_OUTSTAND" NUMBER(20,2), "TOTAL_AMT_OUTSTAND" NUMBER(20,2), "REMARKS" VARCHAR2(200), "TRANSACTION_ID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RDB_OUT_DEFAULT_BACKUP
--------------------------------------------------------

  CREATE TABLE "CIMS_RDB_OUT_DEFAULT_BACKUP" ("SR_NO" NUMBER, "BORROWER_PAN" VARCHAR2(200), "BORROWER_NAME" VARCHAR2(100), "DT_MOVING_OUT_DEFAULT" VARCHAR2(100), "FUND_AMT_OUTSTAND" NUMBER(20,2), "NON_FUND_AMT_OUTSTAND" NUMBER(20,2), "TOTAL_AMT_OUTSTAND" NUMBER(20,2), "REMARKS" VARCHAR2(200), "TRANSACTION_ID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RDB_SIGNATORY
--------------------------------------------------------

  CREATE TABLE "CIMS_RDB_SIGNATORY" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RLC_Q_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_RLC_Q_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RLC_Q_SIGNATORY
--------------------------------------------------------

  CREATE TABLE "CIMS_RLC_Q_SIGNATORY" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RLC_SEC_A
--------------------------------------------------------

  CREATE TABLE "CIMS_RLC_SEC_A" ("SR_NO" NUMBER(20,4), "PAN" VARCHAR2(100), "CUSTOMER_NAME" VARCHAR2(1000), "INDUSTRY_CODE" VARCHAR2(1000), "INDUSTRY_NAME" VARCHAR2(1000), "SECTOR_CODE" VARCHAR2(1000), "BANKING_ARRANGEMENT" VARCHAR2(1000), "LEAD_BANK_CODE" VARCHAR2(1000), "INTERNAL_RATING" VARCHAR2(1000), "EXTERNAL_RATING" VARCHAR2(1000), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "LIMIT_SANCTIONED_FUNDED" NUMBER(20,2), "TOTAL_FUNDED_OUTSTANDING" NUMBER(20,2), "AMT_ELIGIBLE_NETNG_FUNDEDEXPO" NUMBER(20,2), "FUNDED_CREDIT_EXPOSURE" NUMBER(20,2), "LIMIT_SANCTIONED_NON_FUNDED" NUMBER(20,2), "TOTAL_NONFUNDED_OUTSTANDING" NUMBER(20,2), "AMT_ELIGIBLE_NETNG_NONFUNDED" NUMBER(20,2), "NONFUNDED_CREDIT_EXPOSURE" NUMBER(20,2), "TOT_LIMIT_SANC_TO_BROW" NUMBER(20,2), "TOT_AMT_OUT_ST" NUMBER(20,2), "TOT_CREDIT_EXP" NUMBER(20,2), "TEC_PER_CAP_FUND" NUMBER(20,4), "TOTAL_INVESTMENT_EXPOSURE" NUMBER(20,2), "TOTAL_EXPOSURE" NUMBER(20,2), "TE_PER_OF_CAP_FUND" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RLC_SEC_A_CAPITAL_FUND
--------------------------------------------------------

  CREATE TABLE "CIMS_RLC_SEC_A_CAPITAL_FUND" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "RDATE" DATE, "CODE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_RLC_SEC_B
--------------------------------------------------------

  CREATE TABLE "CIMS_RLC_SEC_B" ("SR_NO" NUMBER, "BORROWER_GROUP_CODE" VARCHAR2(500), "GROUP_NAME" VARCHAR2(500), "PAN" VARCHAR2(20), "CUSTOMER_NAME" VARCHAR2(1000), "INDUSTRY_CODE" VARCHAR2(1000), "INDUSTRY_NAME" VARCHAR2(1000), "SECTOR_CODE" VARCHAR2(1000), "BANKING_ARRANGEMENT" VARCHAR2(1000), "LEAD_BANK_NAME" VARCHAR2(1000), "INTERNAL_RATING" VARCHAR2(1000), "EXTERNAL_RATING" VARCHAR2(1000), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "LIMIT_SANCTIONED_FUNDED" NUMBER(20,2), "TOTAL_FUNDED_OUTSTANDING" NUMBER(20,2), "AMT_ELIGIBLE_NETNG_FUNDEDEXPO" NUMBER(20,2), "FUNDED_CREDIT_EXPOSURE" NUMBER(20,2), "LIMIT_SANCTIONED_NON_FUNDED" NUMBER(20,2), "TOTAL_NONFUNDED_OUTSTANDING" NUMBER(20,2), "AMT_ELIGIBLE_NETNG_NONFUNDED" NUMBER(20,2), "NONFUNDED_CREDIT_EXPOSURE" NUMBER(20,2), "TOT_LIMIT_SANC_TO_BROW" NUMBER(20,2), "TOT_AMT_OUT_ST" NUMBER(20,2), "TOT_CREDIT_EXP" NUMBER(20,2), "TEC_PER_CAP_FUND" NUMBER(20,4), "TOTAL_INVESTMENT_EXPOSURE" NUMBER(20,2), "TOTAL_EXPOSURE" NUMBER(20,2), "TE_PER_OF_CAP_FUND" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RLC_SEC_C_FOREIGN
--------------------------------------------------------

  CREATE TABLE "CIMS_RLC_SEC_C_FOREIGN" ("SR_NO" NUMBER, "CUNTR_PARTY_BK_NAME" VARCHAR2(500), "CUNTR_PARTY_BK_DOMICILE" VARCHAR2(500), "FUNDED_EXP" NUMBER(20,2), "NON_FUNDED_EXP" NUMBER(20,2), "TOTAL_EXP" NUMBER(20,2), "TE_CAPITAL_FUND" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RLC_SEC_C_GLOBAL
--------------------------------------------------------

  CREATE TABLE "CIMS_RLC_SEC_C_GLOBAL" ("SR_NO" NUMBER, "CUNTR_PARTY_BK_NAME" VARCHAR2(500), "CUNTR_PARTY_BK_DOMICILE" VARCHAR2(500), "FUNDED_EXP" NUMBER(20,2), "NON_FUNDED_EXP" NUMBER(20,2), "TOTAL_EXP" NUMBER(20,2), "TE_CAPITAL_FUND" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RLC_SEC_C_INDIAN
--------------------------------------------------------

  CREATE TABLE "CIMS_RLC_SEC_C_INDIAN" ("SR_NO" NUMBER, "CUNTR_PARTY_BK_NAME" VARCHAR2(500), "CUNTR_PARTY_BK_DOMICILE" VARCHAR2(500), "FUNDED_EXP" NUMBER(20,2), "NON_FUNDED_EXP" NUMBER(20,2), "TOTAL_EXP" NUMBER(20,2), "TE_CAPITAL_FUND" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RLE_Q_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_RLE_Q_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RLE_Q_SECI
--------------------------------------------------------

  CREATE TABLE "CIMS_RLE_Q_SECI" ("SR_NO" NUMBER, "COUNTRY_CODE" VARCHAR2(2), "BRANCH_CODE" NUMBER(3), "BORR_NAME" VARCHAR2(100), "BORR_GRP_NAME" VARCHAR2(200), "REG_NO" NUMBER(20), "CATG_NEW_EXIST" VARCHAR2(20), "SOV_CHAR" VARCHAR2(100), "TOTAL_LMT_SCNTD" NUMBER(20,2), "FND_LTD_SANC" NUMBER(20,2), "NON_FND_LTD_SANC" NUMBER(20,2), "A_AMT_OS" NUMBER(20,2), "B_SEC_VALUE" NUMBER(20,2), "ASSETS_CLASS" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RLE_Q_SECII
--------------------------------------------------------

  CREATE TABLE "CIMS_RLE_Q_SECII" ("SR_NO" NUMBER, "COUNTRY_CODE" VARCHAR2(2), "BRANCH_CODE" NUMBER(3), "BORR_NAME" VARCHAR2(100), "BORR_GRP_NAME" VARCHAR2(200), "REG_NO" NUMBER(20), "CATG_NEW_EXIST" VARCHAR2(20), "SOV_CHAR" VARCHAR2(100), "TOTAL_LMT_SCNTD" NUMBER(20,2), "FND_LTD_SANC" NUMBER(20,2), "NON_FND_LTD_SANC" NUMBER(20,2), "A_AMT_OS" NUMBER(20,2), "B_SEC_VALUE" NUMBER(20,2), "ASSETS_CLASS" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RLE_Q_SECIII
--------------------------------------------------------

  CREATE TABLE "CIMS_RLE_Q_SECIII" ("SR_NO" NUMBER, "COUNTRY_CODE" VARCHAR2(2), "BRANCH_CODE" NUMBER(3), "CATEGORIES" VARCHAR2(200), "AMT" NUMBER(20,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RLE_Q_SECII_TOTAL
--------------------------------------------------------

  CREATE TABLE "CIMS_RLE_Q_SECII_TOTAL" ("SR_NO" NUMBER, "COUNTRY_CODE" VARCHAR2(2), "BRANCH_CODE" NUMBER(3), "DESCRIPTION" VARCHAR2(100), "TOTAL_LMT_SCNTD" NUMBER(20,2), "FND_LTD_SANC" NUMBER(20,2), "NON_FND_LTD_SANC" NUMBER(20,2), "A_AMT_OS" NUMBER(20,2), "B_SEC_VALUE" NUMBER(20,2), "ASSETS_CLASS" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_RLE_Q_SECI_TOTAL
--------------------------------------------------------

  CREATE TABLE "CIMS_RLE_Q_SECI_TOTAL" ("SR_NO" NUMBER, "COUNTRY_CODE" VARCHAR2(2), "BRANCH_CODE" NUMBER(3), "DESCRIPTION" VARCHAR2(100), "TOTAL_LMT_SCNTD" NUMBER(20,2), "FND_LTD_SANC" NUMBER(20,2), "NON_FND_LTD_SANC" NUMBER(20,2), "A_AMT_OS" NUMBER(20,2), "B_SEC_VALUE" NUMBER(20,2), "ASSETS_CLASS" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ROC_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_ROC_GEN_INFO" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ROC_SEC1_PART_A
--------------------------------------------------------

  CREATE TABLE "CIMS_ROC_SEC1_PART_A" ("SR_NO" NUMBER, "NAME" VARCHAR2(200), "STATUS" VARCHAR2(100), "SHARE_HELD" NUMBER(20,2), "SHARE_TOTAL_EQUITY" NUMBER, "BOOK_VALUE_SHARE_HELD" NUMBER(20,2), "FACE_VALUE_SHARE_HELD" NUMBER(20,2), "TRANSACTION_ID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ROC_SEC1_PART_A_OWNER
--------------------------------------------------------

  CREATE TABLE "CIMS_ROC_SEC1_PART_A_OWNER" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ROC_SEC1_PART_B
--------------------------------------------------------

  CREATE TABLE "CIMS_ROC_SEC1_PART_B" ("PART_B_OTHER_SHAREHOLDER" VARCHAR2(200), "NO_SHARE_HOLDER" NUMBER, "SHARE_HELD" NUMBER(20,2), "SHARE_TOTAL_EQUITY" NUMBER, "BOOK_VALUE_SHARE_HELD" NUMBER(20,2), "FACE_VALUE_SHARE_HELD" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ROC_SEC1_PART_C
--------------------------------------------------------

  CREATE TABLE "CIMS_ROC_SEC1_PART_C" ("OWNERSHIP_SUMMARY" VARCHAR2(200), "RESIDENT" NUMBER(20,4), "NONRESIDENT" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ROC_SEC1_PART_D
--------------------------------------------------------

  CREATE TABLE "CIMS_ROC_SEC1_PART_D" ("SR_NO" NUMBER, "NAME_CONTROLLER_SIGNIFICANT" VARCHAR2(200), "NO_SHARE_HELD" NUMBER, "HOLDING_TOTAL_EQUITY" NUMBER(20,2), "RESIDENCE_STATUS" VARCHAR2(200), "NAME_ASSOCIATE_SHAREHOLDER" VARCHAR2(200), "THEIR_RESIDENCE_STATUS" VARCHAR2(200), "TRANSACTION_ID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ROC_SEC2_PART_A
--------------------------------------------------------

  CREATE TABLE "CIMS_ROC_SEC2_PART_A" ("SR_NO" NUMBER, "NAME_DIRECTOR" VARCHAR2(200), "OCCUPATION" VARCHAR2(200), "ADDRESS" VARCHAR2(200), "APPOINTED_BOARD" VARCHAR2(100), "BOARD_COMMITTEE_MEMBER" VARCHAR2(200), "OTHER_COMMITTEE_DIRECTOR_HELD" VARCHAR2(200), "NATURE_INTEREST_OTHER_COMP" VARCHAR2(200), "TRANSACTION_ID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ROC_SEC2_PART_B
--------------------------------------------------------

  CREATE TABLE "CIMS_ROC_SEC2_PART_B" ("SR_NO" NUMBER, "NAME_DIRECTOR" VARCHAR2(200), "OCCUPATION" VARCHAR2(200), "ADDRESS" VARCHAR2(200), "APPOINTED_BOARD" VARCHAR2(100), "BOARD_COMMITTEE_MEMBER" VARCHAR2(200), "OTHER_COMMITTEE_DIRECTOR_HELD" VARCHAR2(200), "NATURE_INTEREST_OTHER_COMP" VARCHAR2(200), "TRANSACTION_ID" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ROC_SEC2_PART_C
--------------------------------------------------------

  CREATE TABLE "CIMS_ROC_SEC2_PART_C" ("SR_NO" NUMBER, "EXECUTIVE" VARCHAR2(200), "NAME" VARCHAR2(200), "DESIGNATION" VARCHAR2(200), "IN_BANK" VARCHAR2(50), "TO_INCUMBENT_POSITION" VARCHAR2(50), "LOCATED_AT" VARCHAR2(200), "STDCODE" VARCHAR2(50), "LANDLINE1" NUMBER, "LANDLINE2" NUMBER, "MOBILE" NUMBER, "OFF_EMAIL_ID" VARCHAR2(200), "ALT_EMAIL_ID" VARCHAR2(200), "FAXNO" NUMBER, "ALT_NAME" VARCHAR2(200), "ALT_OFF_EMAIL_ID" VARCHAR2(200), "ALT_MOBILE" NUMBER, "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ROC_SEC2_PART_D
--------------------------------------------------------

  CREATE TABLE "CIMS_ROC_SEC2_PART_D" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ROC_SIGNATORY
--------------------------------------------------------

  CREATE TABLE "CIMS_ROC_SIGNATORY" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ROP_MAIN
--------------------------------------------------------

  CREATE TABLE "CIMS_ROP_MAIN" ("SR_NO" NUMBER, "COUNTRY_CODE" VARCHAR2(2), "BRANCH_CODE" NUMBER(3), "DESCRIPTION" VARCHAR2(200), "CURRENT_QUARTER" NUMBER(20,2), "CUMULATIVE_POS" NUMBER(20,2), "CODE" NUMBER(10), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ROP_Q_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_ROP_Q_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ROR_Q_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_ROR_Q_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ROR_Q_SEC_A
--------------------------------------------------------

  CREATE TABLE "CIMS_ROR_Q_SEC_A" ("SR_NO" NUMBER, "ITEM" VARCHAR2(500), "DOM_CURR_QTR" NUMBER, "DOM_CURR_YR_FROM_APR" NUMBER, "OVER_CURR_QTR" NUMBER, "OVER_CURR_YR_FROM_APR" NUMBER, "GLB_CURR_QTR" NUMBER, "GLB_CURR_YR_FROM_APR" NUMBER, "CODE" NUMBER, "RDATE" DATE, "TYP_ID" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table CIMS_ROR_Q_SEC_A1
--------------------------------------------------------

  CREATE TABLE "CIMS_ROR_Q_SEC_A1" ("SR_NO" NUMBER, "LINE_ITEM" VARCHAR2(100), "DOMESTIC" NUMBER, "OVERSEAS" NUMBER, "GLOBAL" NUMBER, "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ROR_Q_SEC_B
--------------------------------------------------------

  CREATE TABLE "CIMS_ROR_Q_SEC_B" ("SR_NO" NUMBER, "LINE_ITEM" VARCHAR2(500), "DOM_OP" NUMBER, "OVER_OP" NUMBER, "GLB_OP" NUMBER, "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ROR_Q_SEC_C
--------------------------------------------------------

  CREATE TABLE "CIMS_ROR_Q_SEC_C" ("SR_NO" NUMBER, "COUNTRY_NAME" VARCHAR2(100), "COUNTRY_CODE" VARCHAR2(20), "LINE_ITEM" VARCHAR2(500), "OVR_BR_NO" NUMBER, "OVR_BR_AMT" NUMBER, "OVR_SUBSIDY_NO" NUMBER, "OVR_SUBSIDY_AMT" NUMBER, "OVR_JOIN_VEN_NO" NUMBER, "OVE_JOIN_VEN_AMT" NUMBER, "TOTAL_NO" NUMBER, "TOTAL_AMT" NUMBER, "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ROR_Q_SIGN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_ROR_Q_SIGN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ROS_HY_DETAILS
--------------------------------------------------------

  CREATE TABLE "CIMS_ROS_HY_DETAILS" ("SUB_ASSO_JV_NAME" VARCHAR2(100), "DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ROS_HY_DETAILS_1
--------------------------------------------------------

  CREATE TABLE "CIMS_ROS_HY_DETAILS_1" ("SUB_ASSO_JV_NAME" VARCHAR2(100), "DESCRIPTION" VARCHAR2(100), "VALUE" NUMBER(20,2), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_ROS_HY_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_ROS_HY_GEN_INFO" ("DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_SECTOR_CODE_MASTER
--------------------------------------------------------

  CREATE TABLE "CIMS_SECTOR_CODE_MASTER" ("SECTOR_CODE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table CIMS_VMR1_Q_FRAUD_CORRUP
--------------------------------------------------------

  CREATE TABLE "CIMS_VMR1_Q_FRAUD_CORRUP" ("SR_NO" VARCHAR2(100), "PARTICULARS" VARCHAR2(200), "FRAUDS" VARCHAR2(100), "CORRUPT_PRACTICES" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_VMR1_Q_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_VMR1_Q_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_VMR1_Q_PART1
--------------------------------------------------------

  CREATE TABLE "CIMS_VMR1_Q_PART1" ("DESCRIPTION" VARCHAR2(200), "ACTION_REQ" VARCHAR2(100), "QT_FIRST" VARCHAR2(100), "QT_SECOND" VARCHAR2(100), "QT_THIRD" VARCHAR2(100), "QT_FOURTH" VARCHAR2(100), "REMARK" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_VMR1_Q_PART2_FIRST
--------------------------------------------------------

  CREATE TABLE "CIMS_VMR1_Q_PART2_FIRST" ("DESCRIPTION" VARCHAR2(200), "STUDY_COMPLETED" VARCHAR2(100), "DATE_OF_IMPLEMENT" VARCHAR2(100), "REMARK" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_VMR1_Q_PART2_SECOND
--------------------------------------------------------

  CREATE TABLE "CIMS_VMR1_Q_PART2_SECOND" ("DESCRIPTION" VARCHAR2(200), "NUM_BER" VARCHAR2(100), "CASE_DETECTED" VARCHAR2(100), "ACTION_TAKEN" VARCHAR2(100), "REMARK" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_VMR1_Q_PART2_THIRD
--------------------------------------------------------

  CREATE TABLE "CIMS_VMR1_Q_PART2_THIRD" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_VMR1_Q_PART3
--------------------------------------------------------

  CREATE TABLE "CIMS_VMR1_Q_PART3" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_VMR1_Q_PART4
--------------------------------------------------------

  CREATE TABLE "CIMS_VMR1_Q_PART4" ("DESCRIPTION" VARCHAR2(200), "LESS_THAN_3_MNTH" VARCHAR2(100), "BETW_3TO6_MNTH" VARCHAR2(100), "BETW_6TO12_MNTH" VARCHAR2(100), "BETW_OVER_1_YER" VARCHAR2(100), "CASE_ID" VARCHAR2(100), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_VMR1_Q_PART5
--------------------------------------------------------

  CREATE TABLE "CIMS_VMR1_Q_PART5" ("DESCRIPTION" VARCHAR2(200), "EMPLOYEE_PSB_FI_CVC" VARCHAR2(100), "OTHER" VARCHAR2(100), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table CIMS_VMR1_Q_SIGN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_VMR1_Q_SIGN_INFO" ("DESCRIPTION" VARCHAR2(200), "AUTH_REPORT_OFFICAL" VARCHAR2(100), "COUNTERSIGNED_BY" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_VMR2_Q_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_VMR2_Q_GEN_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_VMR2_Q_SECURTY_ARRANG
--------------------------------------------------------

  CREATE TABLE "CIMS_VMR2_Q_SECURTY_ARRANG" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIMS_VMR2_Q_SIGN_INFO
--------------------------------------------------------

  CREATE TABLE "CIMS_VMR2_Q_SIGN_INFO" ("DESCRIPTION" VARCHAR2(200), "AUTH_REPORT_OFFICAL" VARCHAR2(100), "COUNTERSIGNED_BY" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table CIRCLEMASTER
--------------------------------------------------------

  CREATE TABLE "CIRCLEMASTER" ("PANNO" VARCHAR2(10), "CUSTBORROWERNAME" VARCHAR2(100), "CIRCLE" VARCHAR2(50), "BRANCHCODE" VARCHAR2(50), "BRANCHNAME" VARCHAR2(150), "CIF" VARCHAR2(50), "REPORTINGDATE" DATE, "CIRCLEUPLOADDATE" VARCHAR2(50));

--------------------------------------------------------
--  DDL for Table CIRCLEMASTER1
--------------------------------------------------------

  CREATE TABLE "CIRCLEMASTER1" ("PANNO" NUMBER, "CIRCLE" VARCHAR2(100), "BRANCHCODE" VARCHAR2(50), "CIF" NUMBER);

--------------------------------------------------------
--  DDL for Table CONTROLTABLE
--------------------------------------------------------

  CREATE TABLE "CONTROLTABLE" ("SR_NO" NUMBER, "FILE_NAME" VARCHAR2(100), "FREQUENCY" VARCHAR2(50), "VALIDATION_STATUS" NUMBER, "CREATED_BY" VARCHAR2(50), "RETURN_CODE" VARCHAR2(11), "RECORD_STATUS" VARCHAR2(20), "REPORTING_DATE" DATE, "VALIDATION_FILE" VARCHAR2(100), "RENDER_FILE" VARCHAR2(100), "GAP" VARCHAR2(20), "GAP_FILE" VARCHAR2(100), "SUBMIT_REPORT" VARCHAR2(20), "ISAUDITED" NUMBER);

--------------------------------------------------------
--  DDL for Table CONTROLTABLE_EY
--------------------------------------------------------

  CREATE TABLE "CONTROLTABLE_EY" ("SR_NO" NUMBER, "REPORT_ID" NUMBER, "REPORT_NAME" VARCHAR2(100), "FREQUENCY" VARCHAR2(50), "RETURN_CODE" VARCHAR2(11), "RECORD_STATUS" VARCHAR2(20), "REPORTING_DATE" DATE);

--------------------------------------------------------
--  DDL for Table CONTROLTABLE_OLD
--------------------------------------------------------

  CREATE TABLE "CONTROLTABLE_OLD" ("SR_NO" NUMBER, "FILE_NAME" VARCHAR2(100), "FREQUENCY" VARCHAR2(50), "VALIDATION_STATUS" NUMBER, "CREATED_BY" VARCHAR2(50), "RETURN_CODE" VARCHAR2(11), "RECORD_STATUS" VARCHAR2(20), "REPORTING_DATE" DATE, "VALIDATION_FILE" VARCHAR2(100), "RENDER_FILE" VARCHAR2(100), "GAP" VARCHAR2(20), "GAP_FILE" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table CONTROLTABLE_ORG
--------------------------------------------------------

  CREATE TABLE "CONTROLTABLE_ORG" ("SR_NO" NUMBER, "REPORT_ID" NUMBER, "BANK_PROFILE_ID" NUMBER, "INSTANCE_NO" NUMBER, "REPORT_NAME" VARCHAR2(100), "DEPT_NAME" VARCHAR2(100), "FILE_NAME" VARCHAR2(100), "OUTPUT_TYPE" VARCHAR2(11), "FREQUENCY" VARCHAR2(50), "PERIOD" VARCHAR2(50), "FISCAL_YEAR" VARCHAR2(50), "LAST_DATE_SUBMITTED" DATE, "NEXT_DUE_DATE" DATE, "CRRT_RECORD_STATUS" NUMBER, "IMPORT_STATUS" NUMBER, "IMPORT_RESPONSE_CODE" NUMBER, "VALIDATION_STATUS" NUMBER, "EFFECTIVE_FROM_TIME_KEY" VARCHAR2(11), "EFFECTIVE_TO_TIME_KEY" VARCHAR2(11), "CREATED_BY" VARCHAR2(50), "CREATED_DT" FLOAT, "MODIFY_BY" VARCHAR2(50), "MODIFIED_DT" FLOAT, "APPROVED_BY" VARCHAR2(50), "XBRL_DATA_FLAG" VARCHAR2(11), "VERSION_NO" VARCHAR2(11), "REPORT_TYPE" VARCHAR2(11), "REPORT_FREQUENCY_APPLY" VARCHAR2(11), "MENU_ID" NUMBER, "MULTIPLE_DOC_UPLOAD_YN" VARCHAR2(11), "BANK_IFSC_CODE" VARCHAR2(50), "RETURN_CODE" VARCHAR2(11), "SUBMISSION_ID" NUMBER, "RECORD_STATUS" VARCHAR2(20), "REPORTING_DATE" DATE, "VALIDATION_FILE" VARCHAR2(100), "RENDER_FILE" VARCHAR2(100), "GAP" VARCHAR2(20), "GAP_FILE" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table COUNTRY_MASTER_CIMS
--------------------------------------------------------

  CREATE TABLE "COUNTRY_MASTER_CIMS" ("COUNTRYNAME" VARCHAR2(200), "COUNTRYCODE" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table CURRENCY_MASTER_CIMS
--------------------------------------------------------

  CREATE TABLE "CURRENCY_MASTER_CIMS" ("CURRENCYNAME" VARCHAR2(200), "CURRENCYSHORTNAME" VARCHAR2(200), "CURRENCYISOCODE" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table C_AUTOPOPULATE
--------------------------------------------------------

  CREATE TABLE "C_AUTOPOPULATE" ("SHEET_NAME" VARCHAR2(250), "MASTER_FIELD" VARCHAR2(250), "MASTER_TABLE" VARCHAR2(250), "AUTO_POPULATE_FIELD" VARCHAR2(250), "AUTO_POPULATE_TABLE" VARCHAR2(250), "AUTO_POP_REF" VARCHAR2(250), "MASTER_REF" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table C_CRILC_CAPITALFUND
--------------------------------------------------------

  CREATE TABLE "C_CRILC_CAPITALFUND" ("RPT_SR_NO" NUMBER, "REGULATORY_CAPITAL_T1" VARCHAR2(250), "CAPITAL_INFUSION_T1" NUMBER, "REGULATORY_CAPITAL_T2" NUMBER, "CAPITAL_INFUSION_T2" NUMBER, "REPORTING_DATE" VARCHAR2(50));

--------------------------------------------------------
--  DDL for Table C_CRILC_CAPITALFUND1
--------------------------------------------------------

  CREATE TABLE "C_CRILC_CAPITALFUND1" ("RPT_SR_NO" NUMBER, "REGULATORY_CAPITAL_T1" VARCHAR2(250), "CAPITAL_INFUSION_T1" VARCHAR2(250), "REGULATORY_CAPITAL_T2" VARCHAR2(250), "CAPITAL_INFUSION_T2" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(50));

--------------------------------------------------------
--  DDL for Table C_CRILC_CAPITALFUND_RENDERED
--------------------------------------------------------

  CREATE TABLE "C_CRILC_CAPITALFUND_RENDERED" ("RPT_SR_NO" NUMBER, "REGULATORY_CAPITAL_T1" VARCHAR2(250), "CAPITAL_INFUSION_T1" NUMBER, "REGULATORY_CAPITAL_T2" NUMBER, "CAPITAL_INFUSION_T2" NUMBER, "REPORTING_DATE" VARCHAR2(50));

--------------------------------------------------------
--  DDL for Table C_CRILC_GENERAL_INFO
--------------------------------------------------------

  CREATE TABLE "C_CRILC_GENERAL_INFO" ("CODE" VARCHAR2(20), "DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(500), "REPORTING_DATE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table C_CRILC_GENERAL_INFO1
--------------------------------------------------------

  CREATE TABLE "C_CRILC_GENERAL_INFO1" ("CODE" VARCHAR2(20), "DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(500), "REPORING_DATE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table C_CRILC_GENERAL_INFO_RENDERED
--------------------------------------------------------

  CREATE TABLE "C_CRILC_GENERAL_INFO_RENDERED" ("CODE" VARCHAR2(20), "DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(500), "REPORTING_DATE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table C_CRILC_SECTION1_TOTAL
--------------------------------------------------------

  CREATE TABLE "C_CRILC_SECTION1_TOTAL" ("RPT_SR_NO" NUMBER, "AGGREGATE_FUND_BASED_WC_LIMIT" VARCHAR2(45), "OF_WHICH_INTRA_CR_LIMIT" VARCHAR2(45), "LIMIT_SANCTIONED_FUNDED" NUMBER, "CASHCREDIT_OVERDRAFT" VARCHAR2(45), "WORKINGCAPITAL_DEMANDLOAN" NUMBER, "INLAND_BILLS" NUMBER, "PACKING_CREDIT" NUMBER, "EXPORT_BILLS" NUMBER, "TERM_LOAN" NUMBER, "BLS_DC_RSPT_SLS_ON_DFRD_PMT_BS" NUMBER, "OTHER_FUNDED_OUTSTANDING" NUMBER, "TOTAL_FUNDED_OUTSTANDING" NUMBER, "AMT_ELGB_FRNTG_FRM_FNDEDEXP" NUMBER, "FUNDED_CREDIT_EXPOSURE" VARCHAR2(45), "SECURED_FUNDED_AMT" VARCHAR2(45), "LIMIT_SANCTIONED_NONFUNDED" NUMBER, "LETTER_OF_CREDIT" NUMBER, "GUARANTEES" NUMBER, "ACCEPTANCES" VARCHAR2(45), "FOREIGN_EXCHANGE_CONTRACTS" NUMBER, "INRT_RT_DRVT_INC_INRT_RT_DRVT" VARCHAR2(45), "OTHER_NONFUNDED_OUTSTANDING" NUMBER, "TOTAL_NONFUNDED_OUTSTANDING" VARCHAR2(45), "AMT_ELGB_FRNTG_FRM_NONFNDEDEXP" NUMBER, "NON_FUNDED_CREDIT_EXPOSURE" NUMBER, "TOTAL_LIMIT_SANCTIONED_TOBRWR" NUMBER, "TOTAL_AMT_OTNG_FUNDEDNONFUNDED" NUMBER, "OF_WHICHADDITIONAL_FINANCE" VARCHAR2(45), "TOTAL_CREDIT_EXPOSURE" NUMBER, "TOTAL_CREDIT_EXPO_CRM" VARCHAR2(45), "TCEAS_PER_OF_CAPITAL_FUNDS" VARCHAR2(45), "TOTAL_INVESTMENT_EXPOSURE" NUMBER, "TOTAL_EXPOSURE" NUMBER, "OFTE_FOREIGN_CURRENCY_EXPOSURE" NUMBER, "TOTAL_EXPOSURE_CRM" VARCHAR2(45), "TEASPEROF_CAPITAL_FUNDS" VARCHAR2(45), "OF_EXP_THG_OVS_BRNCS_OF_INBNKS" NUMBER, "TOTAL_PROVISION_SHELDFORNPAS" NUMBER, "DICGCECGCCGMTMSE_OTHER_CLAIMS" VARCHAR2(250), "OF_TOT_AMT_OUTSTD_FNDNFNDSECRD" NUMBER, "BALANCE_INCURRENT_ACCOUNT" VARCHAR2(45), "AMT_TECHNICALLY_PRUDENTIALLY" NUMBER, "WO_THROUGH_SETTLE" VARCHAR2(45), "OTHER_WO" VARCHAR2(45), "TOTAL_WO" VARCHAR2(45), "REPORTING_DATE" VARCHAR2(50));

--------------------------------------------------------
--  DDL for Table C_CRILC_SECTION1_TOTAL1
--------------------------------------------------------

  CREATE TABLE "C_CRILC_SECTION1_TOTAL1" ("RPT_SR_NO" NUMBER, "AGGREGATE_FUND_BASED_WC_LIMIT" VARCHAR2(45), "OF_WHICH_INTRA_CR_LIMIT" VARCHAR2(45), "LIMIT_SANCTIONED_FUNDED" VARCHAR2(45), "CASHCREDIT_OVERDRAFT" VARCHAR2(45), "WORKINGCAPITAL_DEMANDLOAN" VARCHAR2(45), "INLAND_BILLS" VARCHAR2(45), "PACKING_CREDIT" VARCHAR2(45), "EXPORT_BILLS" VARCHAR2(45), "TERM_LOAN" VARCHAR2(45), "BLS_DC_RSPT_SLS_ON_DFRD_PMT_BS" VARCHAR2(45), "OTHER_FUNDED_OUTSTANDING" VARCHAR2(45), "TOTAL_FUNDED_OUTSTANDING" VARCHAR2(45), "AMT_ELGB_FRNTG_FRM_FNDEDEXP" VARCHAR2(45), "FUNDED_CREDIT_EXPOSURE" VARCHAR2(45), "SECURED_FUNDED_AMT" VARCHAR2(45), "LIMIT_SANCTIONED_NONFUNDED" VARCHAR2(45), "LETTER_OF_CREDIT" VARCHAR2(45), "GUARANTEES" VARCHAR2(45), "ACCEPTANCES" VARCHAR2(45), "FOREIGN_EXCHANGE_CONTRACTS" VARCHAR2(45), "INRT_RT_DRVT_INC_INRT_RT_DRVT" VARCHAR2(45), "OTHER_NONFUNDED_OUTSTANDING" VARCHAR2(45), "TOTAL_NONFUNDED_OUTSTANDING" VARCHAR2(45), "AMT_ELGB_FRNTG_FRM_NONFNDEDEXP" VARCHAR2(45), "NON_FUNDED_CREDIT_EXPOSURE" VARCHAR2(45), "TOTAL_LIMIT_SANCTIONED_TOBRWR" VARCHAR2(45), "TOTAL_AMT_OTNG_FUNDEDNONFUNDED" VARCHAR2(45), "OF_WHICHADDITIONAL_FINANCE" VARCHAR2(45), "TOTAL_CREDIT_EXPOSURE" VARCHAR2(45), "TOTAL_CREDIT_EXPO_CRM" VARCHAR2(45), "TCEAS_PER_OF_CAPITAL_FUNDS" VARCHAR2(45), "TOTAL_INVESTMENT_EXPOSURE" VARCHAR2(45), "TOTAL_EXPOSURE" VARCHAR2(45), "OFTE_FOREIGN_CURRENCY_EXPOSURE" VARCHAR2(250), "TOTAL_EXPOSURE_CRM" VARCHAR2(45), "TEASPEROF_CAPITAL_FUNDS" VARCHAR2(45), "OF_EXP_THG_OVS_BRNCS_OF_INBNKS" VARCHAR2(45), "TOTAL_PROVISION_SHELDFORNPAS" VARCHAR2(45), "DICGCECGCCGMTMSE_OTHER_CLAIMS" VARCHAR2(250), "OF_TOT_AMT_OUTSTD_FNDNFNDSECRD" VARCHAR2(45), "BALANCE_INCURRENT_ACCOUNT" VARCHAR2(45), "AMT_TECHNICALLY_PRUDENTIALLY" VARCHAR2(45), "WO_THROUGH_SETTLE" VARCHAR2(45), "OTHER_WO" VARCHAR2(45), "TOTAL_WO" VARCHAR2(45), "REPORTING_DATE" VARCHAR2(50));

--------------------------------------------------------
--  DDL for Table C_CRILC_SECTION1_TOTAL_RENDERED
--------------------------------------------------------

  CREATE TABLE "C_CRILC_SECTION1_TOTAL_RENDERED" ("RPT_SR_NO" NUMBER, "AGGREGATE_FUND_BASED_WC_LIMIT" VARCHAR2(45), "OF_WHICH_INTRA_CR_LIMIT" VARCHAR2(45), "LIMIT_SANCTIONED_FUNDED" NUMBER, "CASHCREDIT_OVERDRAFT" VARCHAR2(45), "WORKINGCAPITAL_DEMANDLOAN" NUMBER, "INLAND_BILLS" NUMBER, "PACKING_CREDIT" NUMBER, "EXPORT_BILLS" NUMBER, "TERM_LOAN" NUMBER, "BLS_DC_RSPT_SLS_ON_DFRD_PMT_BS" NUMBER, "OTHER_FUNDED_OUTSTANDING" NUMBER, "TOTAL_FUNDED_OUTSTANDING" NUMBER, "AMT_ELGB_FRNTG_FRM_FNDEDEXP" NUMBER, "FUNDED_CREDIT_EXPOSURE" VARCHAR2(45), "SECURED_FUNDED_AMT" VARCHAR2(45), "LIMIT_SANCTIONED_NONFUNDED" NUMBER, "LETTER_OF_CREDIT" NUMBER, "GUARANTEES" NUMBER, "ACCEPTANCES" VARCHAR2(45), "FOREIGN_EXCHANGE_CONTRACTS" NUMBER, "INRT_RT_DRVT_INC_INRT_RT_DRVT" VARCHAR2(45), "OTHER_NONFUNDED_OUTSTANDING" NUMBER, "TOTAL_NONFUNDED_OUTSTANDING" VARCHAR2(45), "AMT_ELGB_FRNTG_FRM_NONFNDEDEXP" NUMBER, "NON_FUNDED_CREDIT_EXPOSURE" NUMBER, "TOTAL_LIMIT_SANCTIONED_TOBRWR" NUMBER, "TOTAL_AMT_OTNG_FUNDEDNONFUNDED" NUMBER, "OF_WHICHADDITIONAL_FINANCE" VARCHAR2(45), "TOTAL_CREDIT_EXPOSURE" NUMBER, "TOTAL_CREDIT_EXPO_CRM" VARCHAR2(45), "TCEAS_PER_OF_CAPITAL_FUNDS" VARCHAR2(45), "TOTAL_INVESTMENT_EXPOSURE" NUMBER, "TOTAL_EXPOSURE" NUMBER, "OFTE_FOREIGN_CURRENCY_EXPOSURE" NUMBER, "TOTAL_EXPOSURE_CRM" VARCHAR2(45), "TEASPEROF_CAPITAL_FUNDS" VARCHAR2(45), "OF_EXP_THG_OVS_BRNCS_OF_INBNKS" NUMBER, "TOTAL_PROVISION_SHELDFORNPAS" NUMBER, "DICGCECGCCGMTMSE_OTHER_CLAIMS" VARCHAR2(250), "OF_TOT_AMT_OUTSTD_FNDNFNDSECRD" NUMBER, "BALANCE_INCURRENT_ACCOUNT" VARCHAR2(45), "AMT_TECHNICALLY_PRUDENTIALLY" NUMBER, "WO_THROUGH_SETTLE" VARCHAR2(45), "OTHER_WO" VARCHAR2(45), "TOTAL_WO" VARCHAR2(45), "REPORTING_DATE" VARCHAR2(50));

--------------------------------------------------------
--  DDL for Table C_CRILC_SECTION1_TOTAL_dp
--------------------------------------------------------

  CREATE TABLE "C_CRILC_SECTION1_TOTAL_dp" ("RPT_SR_NO" NUMBER, "AGGREGATE_FUND_BASED_WC_LIMIT" VARCHAR2(45), "OF_WHICH_INTRA_CR_LIMIT" VARCHAR2(45), "LIMIT_SANCTIONED_FUNDED" NUMBER, "CASHCREDIT_OVERDRAFT" VARCHAR2(45), "WORKINGCAPITAL_DEMANDLOAN" NUMBER, "INLAND_BILLS" NUMBER, "PACKING_CREDIT" NUMBER, "EXPORT_BILLS" NUMBER, "TERM_LOAN" NUMBER, "BLS_DC_RSPT_SLS_ON_DFRD_PMT_BS" NUMBER, "OTHER_FUNDED_OUTSTANDING" NUMBER, "TOTAL_FUNDED_OUTSTANDING" NUMBER, "AMT_ELGB_FRNTG_FRM_FNDEDEXP" NUMBER, "FUNDED_CREDIT_EXPOSURE" VARCHAR2(45), "SECURED_FUNDED_AMT" VARCHAR2(45), "LIMIT_SANCTIONED_NONFUNDED" NUMBER, "LETTER_OF_CREDIT" NUMBER, "GUARANTEES" NUMBER, "ACCEPTANCES" VARCHAR2(45), "FOREIGN_EXCHANGE_CONTRACTS" NUMBER, "INRT_RT_DRVT_INC_INRT_RT_DRVT" VARCHAR2(45), "OTHER_NONFUNDED_OUTSTANDING" NUMBER, "TOTAL_NONFUNDED_OUTSTANDING" VARCHAR2(45), "AMT_ELGB_FRNTG_FRM_NONFNDEDEXP" NUMBER, "NON_FUNDED_CREDIT_EXPOSURE" NUMBER, "TOTAL_LIMIT_SANCTIONED_TOBRWR" NUMBER, "TOTAL_AMT_OTNG_FUNDEDNONFUNDED" NUMBER, "OF_WHICHADDITIONAL_FINANCE" VARCHAR2(45), "TOTAL_CREDIT_EXPOSURE" NUMBER, "TOTAL_CREDIT_EXPO_CRM" VARCHAR2(45), "TCEAS_PER_OF_CAPITAL_FUNDS" VARCHAR2(45), "TOTAL_INVESTMENT_EXPOSURE" NUMBER, "TOTAL_EXPOSURE" NUMBER, "OFTE_FOREIGN_CURRENCY_EXPOSURE" NUMBER, "TOTAL_EXPOSURE_CRM" VARCHAR2(45), "TEASPEROF_CAPITAL_FUNDS" VARCHAR2(45), "OF_EXP_THG_OVS_BRNCS_OF_INBNKS" NUMBER, "TOTAL_PROVISION_SHELDFORNPAS" NUMBER, "DICGCECGCCGMTMSE_OTHER_CLAIMS" VARCHAR2(250), "OF_TOT_AMT_OUTSTD_FNDNFNDSECRD" NUMBER, "BALANCE_INCURRENT_ACCOUNT" VARCHAR2(45), "AMT_TECHNICALLY_PRUDENTIALLY" NUMBER, "WO_THROUGH_SETTLE" VARCHAR2(45), "OTHER_WO" VARCHAR2(45), "TOTAL_WO" VARCHAR2(45), "REPORTING_DATE" VARCHAR2(50));

--------------------------------------------------------
--  DDL for Table C_CRILC_SECTION1_TOTAL_hist
--------------------------------------------------------

  CREATE TABLE "C_CRILC_SECTION1_TOTAL_hist" ("RPT_SR_NO" NUMBER, "AGGREGATE_FUND_BASED_WC_LIMIT" VARCHAR2(45), "OF_WHICH_INTRA_CR_LIMIT" VARCHAR2(45), "LIMIT_SANCTIONED_FUNDED" NUMBER, "CASHCREDIT_OVERDRAFT" VARCHAR2(45), "WORKINGCAPITAL_DEMANDLOAN" NUMBER, "INLAND_BILLS" NUMBER, "PACKING_CREDIT" NUMBER, "EXPORT_BILLS" NUMBER, "TERM_LOAN" NUMBER, "BLS_DC_RSPT_SLS_ON_DFRD_PMT_BS" NUMBER, "OTHER_FUNDED_OUTSTANDING" NUMBER, "TOTAL_FUNDED_OUTSTANDING" NUMBER, "AMT_ELGB_FRNTG_FRM_FNDEDEXP" NUMBER, "FUNDED_CREDIT_EXPOSURE" VARCHAR2(45), "SECURED_FUNDED_AMT" VARCHAR2(45), "LIMIT_SANCTIONED_NONFUNDED" NUMBER, "LETTER_OF_CREDIT" NUMBER, "GUARANTEES" NUMBER, "ACCEPTANCES" VARCHAR2(45), "FOREIGN_EXCHANGE_CONTRACTS" NUMBER, "INRT_RT_DRVT_INC_INRT_RT_DRVT" VARCHAR2(45), "OTHER_NONFUNDED_OUTSTANDING" NUMBER, "TOTAL_NONFUNDED_OUTSTANDING" VARCHAR2(45), "AMT_ELGB_FRNTG_FRM_NONFNDEDEXP" NUMBER, "NON_FUNDED_CREDIT_EXPOSURE" NUMBER, "TOTAL_LIMIT_SANCTIONED_TOBRWR" NUMBER, "TOTAL_AMT_OTNG_FUNDEDNONFUNDED" NUMBER, "OF_WHICHADDITIONAL_FINANCE" VARCHAR2(45), "TOTAL_CREDIT_EXPOSURE" NUMBER, "TOTAL_CREDIT_EXPO_CRM" VARCHAR2(45), "TCEAS_PER_OF_CAPITAL_FUNDS" VARCHAR2(45), "TOTAL_INVESTMENT_EXPOSURE" NUMBER, "TOTAL_EXPOSURE" NUMBER, "OFTE_FOREIGN_CURRENCY_EXPOSURE" NUMBER, "TOTAL_EXPOSURE_CRM" VARCHAR2(45), "TEASPEROF_CAPITAL_FUNDS" VARCHAR2(45), "OF_EXP_THG_OVS_BRNCS_OF_INBNKS" NUMBER, "TOTAL_PROVISION_SHELDFORNPAS" NUMBER, "DICGCECGCCGMTMSE_OTHER_CLAIMS" VARCHAR2(250), "OF_TOT_AMT_OUTSTD_FNDNFNDSECRD" NUMBER, "BALANCE_INCURRENT_ACCOUNT" VARCHAR2(45), "AMT_TECHNICALLY_PRUDENTIALLY" NUMBER, "WO_THROUGH_SETTLE" VARCHAR2(45), "OTHER_WO" VARCHAR2(45), "TOTAL_WO" VARCHAR2(45), "REPORTING_DATE" VARCHAR2(50));

--------------------------------------------------------
--  DDL for Table C_CRILC_SECTION_2_TOTAL
--------------------------------------------------------

  CREATE TABLE "C_CRILC_SECTION_2_TOTAL" ("RPT_SR_NO" NUMBER, "AMOUNT_TECHNI_PRU_WRITOFF" VARCHAR2(250), "WO_THROUGH_SETTLE" VARCHAR2(250), "OTHER_WO" VARCHAR2(250), "TOTAL_WO" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(50));

--------------------------------------------------------
--  DDL for Table C_CRILC_SECTION_2_TOTAL_RENDERED
--------------------------------------------------------

  CREATE TABLE "C_CRILC_SECTION_2_TOTAL_RENDERED" ("RPT_SR_NO" NUMBER, "AMOUNT_TECHNI_PRU_WRITOFF" VARCHAR2(250), "WO_THROUGH_SETTLE" VARCHAR2(250), "OTHER_WO" VARCHAR2(250), "TOTAL_WO" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(50));

--------------------------------------------------------
--  DDL for Table C_CRILC_SECTION_3_TOTAL
--------------------------------------------------------

  CREATE TABLE "C_CRILC_SECTION_3_TOTAL" ("RPT_SR_NO" NUMBER, "BALANCE_IN_CURRENT_ACCOUNT" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(50));

--------------------------------------------------------
--  DDL for Table C_CRILC_SECTION_3_TOTAL_RENDERED
--------------------------------------------------------

  CREATE TABLE "C_CRILC_SECTION_3_TOTAL_RENDERED" ("RPT_SR_NO" NUMBER, "BALANCE_IN_CURRENT_ACCOUNT" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(50));

--------------------------------------------------------
--  DDL for Table C_CRILC_SIGN_INFO
--------------------------------------------------------

  CREATE TABLE "C_CRILC_SIGN_INFO" ("CODE" VARCHAR2(20), "DESCRIPTION" VARCHAR2(20), "VALUE" VARCHAR2(20), "REPORTING_DATE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table C_CRILC_SIGN_INFO_BKUP
--------------------------------------------------------

  CREATE TABLE "C_CRILC_SIGN_INFO_BKUP" ("CODE" VARCHAR2(20), "DESCRIPTION" VARCHAR2(20), "VALUE" VARCHAR2(20), "REPORTING_DATE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table C_CRILC_SIGN_INFO_RENDERED
--------------------------------------------------------

  CREATE TABLE "C_CRILC_SIGN_INFO_RENDERED" ("CODE" VARCHAR2(20), "DESCRIPTION" VARCHAR2(20), "VALUE" VARCHAR2(20), "REPORTING_DATE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table C_DBR01_PART1_RET_ON_COMP_TAB1
--------------------------------------------------------

  CREATE TABLE "C_DBR01_PART1_RET_ON_COMP_TAB1" ("SR_NO" NUMBER, "TYPE_OF_CUSTOMER_COMPLAINTS" VARCHAR2(500), "NO_OF_COMPLAINTS_PENDING_X10" NUMBER, "NO_OF_COMPLAINTS_RECEVIED_X20" NUMBER, "NO_OF_COMPLAINTS_RESOLVED_X30" NUMBER, "NO_OF_COMPLAINTS_PENDING_X40" NUMBER, "REPORT_DATE" DATE);

--------------------------------------------------------
--  DDL for Table C_DBR01_PART1_RET_ON_COMP_TAB2
--------------------------------------------------------

  CREATE TABLE "C_DBR01_PART1_RET_ON_COMP_TAB2" ("SR_NO" NUMBER, "COMPLAINTS_RESOLUTION_BY_DET" VARCHAR2(500), "CODE" VARCHAR2(100), "FULLY_REDRESSED_X50" NUMBER, "PARTIALLY_REDRESSED_X60" NUMBER, "REJECTED_X70" NUMBER, "REPORT_DATE" DATE);

--------------------------------------------------------
--  DDL for Table C_DBR01_PART1_RET_ON_COMP_TAB3
--------------------------------------------------------

  CREATE TABLE "C_DBR01_PART1_RET_ON_COMP_TAB3" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "CODE" VARCHAR2(100), "NUMBER_X80" NUMBER, "REPORT_DATE" DATE);

--------------------------------------------------------
--  DDL for Table C_DBR01_PART1_RET_ON_COMP_TAB4
--------------------------------------------------------

  CREATE TABLE "C_DBR01_PART1_RET_ON_COMP_TAB4" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "CODE" VARCHAR2(100), "NUMBER_OF_ADVISORIES_X90" NUMBER, "REPORT_DATE" DATE);

--------------------------------------------------------
--  DDL for Table C_DBR01_PART1_RET_ON_COMP_TAB5
--------------------------------------------------------

  CREATE TABLE "C_DBR01_PART1_RET_ON_COMP_TAB5" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "CODE" VARCHAR2(100), "NUMBER_OF_AWARDS_X100" NUMBER, "REPORT_DATE" DATE);

--------------------------------------------------------
--  DDL for Table C_DBR01_PART1_RET_ON_COMP_TAB6
--------------------------------------------------------

  CREATE TABLE "C_DBR01_PART1_RET_ON_COMP_TAB6" ("SR_NO" NUMBER, "NATURE_OF_CUST_COMPLAINTS" VARCHAR2(500), "NO_OF_COMPLAINTS_PENDING_X110" NUMBER, "NO_OF_COMPLAINTS_RECEVIED_X120" NUMBER, "NO_OF_COMPLAINTS_RESOLVED_X130" NUMBER, "NO_OF_COMPLAINTS_PENDING_X140" NUMBER, "REMARKS_X150" VARCHAR2(1000), "REPORT_DATE" DATE);

--------------------------------------------------------
--  DDL for Table C_DBR01_PART1_RET_ON_COMP_TAB7
--------------------------------------------------------

  CREATE TABLE "C_DBR01_PART1_RET_ON_COMP_TAB7" ("SR_NO" NUMBER, "NATURE_OF_CUST_COMPLAINTS" VARCHAR2(500), "CUSTOMER_COMPLAINTS_AGING" VARCHAR2(500), "COMPLAINTS_PENDING_X160" NUMBER, "REPORT_DATE" DATE);

--------------------------------------------------------
--  DDL for Table C_DBR01_PART2_RET_ON_COMP_TAB8
--------------------------------------------------------

  CREATE TABLE "C_DBR01_PART2_RET_ON_COMP_TAB8" ("SR_NO" NUMBER, "STATE" VARCHAR2(100), "NATURE_OF_CUST_COMPLAINTS" VARCHAR2(500), "NO_OF_COMPLAINTS_X010" NUMBER, "REPORT_DATE" DATE);

--------------------------------------------------------
--  DDL for Table C_DBR01_PART2_RET_ON_COMP_TAB9
--------------------------------------------------------

  CREATE TABLE "C_DBR01_PART2_RET_ON_COMP_TAB9" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "CODE" VARCHAR2(100), "NO_OF_ACCOUNTS_X020" NUMBER, "REPORT_DATE" DATE);

--------------------------------------------------------
--  DDL for Table C_DBR01_PART3_RET_ON_COMP
--------------------------------------------------------

  CREATE TABLE "C_DBR01_PART3_RET_ON_COMP" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "NO_OF_COMPLAINTS_RECEVIED_X010" NUMBER, "NO_OF_COMPLAINTS_REJECTED_X020" NUMBER, "NO_OF_COMPLAINTS_REFFERED_X030" NUMBER, "REPORT_DATE" DATE);

--------------------------------------------------------
--  DDL for Table C_DBR01_PART4_RET_ON_COMP_TAB1
--------------------------------------------------------

  CREATE TABLE "C_DBR01_PART4_RET_ON_COMP_TAB1" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "NO_OF_COMPLAINTS_REFFERED_X010" NUMBER, "NO_OF_COMPLAINTS_CLOSED_X020" NUMBER, "NO_OF_CASES_DECISION_X030" NUMBER, "NO_OF_IO_DECISIONS_X040" NUMBER, "REPORT_DATE" DATE);

--------------------------------------------------------
--  DDL for Table C_DBR01_PART4_RET_ON_COMP_TAB2
--------------------------------------------------------

  CREATE TABLE "C_DBR01_PART4_RET_ON_COMP_TAB2" ("SR_NO" NUMBER, "PERIODS" VARCHAR2(500), "CODE" VARCHAR2(100), "NO_OF_IO_DECISIONS_X040" NUMBER, "REPORT_DATE" DATE);

--------------------------------------------------------
--  DDL for Table C_IDEAL_CRILC_SECTION_1_ORG
--------------------------------------------------------

  CREATE TABLE "C_IDEAL_CRILC_SECTION_1_ORG" ("RPT_SR_NO" NUMBER, "PAN" VARCHAR2(250), "CUSTOMER_NAME" VARCHAR2(1000), "LEI" VARCHAR2(250), "CIN" VARCHAR2(250), "BORROWER_GROUP_CODE" VARCHAR2(250), "BORROWER_GROUP_NAME" VARCHAR2(1000), "INDUSTRY_CODE" VARCHAR2(1000), "INDUSTRY_NAME" VARCHAR2(1000), "SECTOR_CODE" VARCHAR2(1000), "BANKING_ARRANGEMENT" VARCHAR2(1000), "LEAD_BANK_NAME" VARCHAR2(1000), "INTERNAL_RATING" VARCHAR2(1000), "EXTERNAL_RATING" VARCHAR2(1000), "WHETHER_PROJECT_FINANCE" VARCHAR2(10), "DATE_OF_FINANCIAL_CLOSURE" VARCHAR2(100), "DATE_OF_ORIGINAL_DCCO" VARCHAR2(100), "WHETHER_CREDIT_EVENT_TRIGGERED" VARCHAR2(10), "DATE_OF_CREDT_EVENT" VARCHAR2(100), "REASON_FOR_CREDIT_EVENT" VARCHAR2(250), "DATE_OF_REVISED_DCCO" VARCHAR2(100), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "DATE_NPA_CLASSIFY" VARCHAR2(100), "RESTRUCTING_SCHEME_DATE" VARCHAR2(100), "BRWR_CLASIFID_FRAUD_DEFAULT" VARCHAR2(1000), "DATE_CLASS_WILF_DEFAULT" VARCHAR2(100), "WH_CLASS_RFA_FRAUD" VARCHAR2(1000), "DATE_CLASS_RFA_FRAUD" VARCHAR2(100), "NPA_DUE_FOREIGN_COUNTRY" VARCHAR2(20), "SPECIAL_MENTION_ACCOUNTS" VARCHAR2(1000), "DATE_SMA_CLASSIFY" VARCHAR2(100), "RESOLUTION_PLAN_STATUS" VARCHAR2(250), "DATE_FILING_WITH_NCLT" VARCHAR2(250), "DATE_ADDMISSION" VARCHAR2(250), "LOAN_BUYOUT_TAKEOVER" VARCHAR2(200), "DATE_BUYOUT_TAKEOVER" VARCHAR2(200), "WHETHER_CC_OD_FAC" VARCHAR2(200), "AGGREGATE_FUND_BASED_WC_LIMIT" VARCHAR2(200), "OF_WHICH_INTRA_CR_LIMIT" VARCHAR2(200), "LIMIT_SANCTIONED_FUNDED" VARCHAR2(250), "CASH_CREDIT_OVERDRAFT" VARCHAR2(250), "WORKING_CAPITAL_DEMAND_LOAN" VARCHAR2(250), "INLAND_BILLS" VARCHAR2(250), "PACKING_CREDIT" VARCHAR2(250), "EXPORT_BILLS" VARCHAR2(250), "TERM_LOAN" VARCHAR2(250), "BILLS_DISCONTINUED_DEFRED" VARCHAR2(250), "OTHER_FUNDED_OUTSTANDING" VARCHAR2(250), "TOTAL_FUNDED_OUTSTANDING" VARCHAR2(250), "AMT_ELIGIBLE_NETNG_FUNDEDEXPO" VARCHAR2(250), "FUNDED_CREDIT_EXPOSURE" VARCHAR2(250), "SECURED_FUNDED_AMT" VARCHAR2(200), "LIMIT_SANCTIONED_NON_FUNDED" VARCHAR2(250), "LETTER_OF_CREDIT" VARCHAR2(250), "GUARANTEES" VARCHAR2(250), "ACCEPTANCES" VARCHAR2(250), "FOREIGN_EXCHANGE_CONTRACTS" VARCHAR2(250), "INTEREST_RATE_DERIVATIVES" VARCHAR2(250), "OTHER_NONFUNDED_OUTSTANDING" VARCHAR2(250), "TOTAL_NONFUNDED_OUTSTANDING" VARCHAR2(250), "AMT_ELIGIBLE_NETNG_NONFUNDED" VARCHAR2(250), "NONFUNDED_CREDIT_EXPOSURE" VARCHAR2(250), "TOTAL_LMT_SANCTIONED_BRWR" VARCHAR2(250), "TOTAL_AMT_OUTSTANDING" VARCHAR2(250), "OF_WHICH_ADD_FIN_CLASIFY" VARCHAR2(100), "TOTAL_CREDIT_EXPOSURE" VARCHAR2(250), "TOTAL_CREDIT_EXPO_CRM" VARCHAR2(250), "TCE_AS_PRCNT_OF_CAPITAL_FUNDS" VARCHAR2(250), "TOTAL_INVESTMENT_EXPOSURE" VARCHAR2(250), "TOTAL_EXPOSURE" VARCHAR2(250), "OFTE_FOREIGN_CURRENCY_EXPOSURE" VARCHAR2(250), "TOTAL_EXPOSURE_CRM" VARCHAR2(250), "TE_AS_PRCNT_OF_CAPITAL_FUNDS" VARCHAR2(250), "EXPO_OVERSEAS_BRNCH_INDIANBANK" VARCHAR2(250), "TOTAL_PROVISIONS_HELD_NPA" VARCHAR2(100), "DICGC_ECGC_CGMTMSE_OTHERCLAIMS" VARCHAR2(250), "UNSECURED_AMT_OUTSTANDING" VARCHAR2(250), "CURRENT_ACCOUNT_BALANCE" VARCHAR2(250), "AMT_PRUDENTIALLY_WRITTEN_OFF" VARCHAR2(250), "DATE_PRUDENTIALLY_WRITTEN_OFF" VARCHAR2(200), "WO_THROUGH_SETTLE" VARCHAR2(250), "OTHER_WO" VARCHAR2(250), "TOTAL_WO" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table C_IDEAL_CRILC_SECTION_1_ORG_BACKUP_06_03_26
--------------------------------------------------------

  CREATE TABLE "C_IDEAL_CRILC_SECTION_1_ORG_BACKUP_06_03_26" ("RPT_SR_NO" NUMBER, "PAN" VARCHAR2(250), "CUSTOMER_NAME" VARCHAR2(1000), "LEI" VARCHAR2(25), "CIN" VARCHAR2(25), "BORROWER_GROUP_CODE" VARCHAR2(250), "BORROWER_GROUP_NAME" VARCHAR2(1000), "INDUSTRY_CODE" VARCHAR2(1000), "INDUSTRY_NAME" VARCHAR2(1000), "SECTOR_CODE" VARCHAR2(1000), "BANKING_ARRANGEMENT" VARCHAR2(1000), "LEAD_BANK_NAME" VARCHAR2(1000), "INTERNAL_RATING" VARCHAR2(1000), "EXTERNAL_RATING" VARCHAR2(1000), "ASSETS_CLASSIFICATION" VARCHAR2(250), "DATE_NPA_CLASSIFY" VARCHAR2(100), "RESTRUCTING_SCHEME_DATE" VARCHAR2(100), "BRWR_CLASIFID_FRAUD_DEFAULT" VARCHAR2(1000), "DATE_CLASS_WILF_DEFAULT" VARCHAR2(100), "WH_CLASS_RFA_FRAUD" VARCHAR2(1000), "DATE_CLASS_RFA_FRAUD" VARCHAR2(100), "NPA_DUE_FOREIGN_COUNTRY" VARCHAR2(20), "SPECIAL_MENTION_ACCOUNTS" VARCHAR2(1000), "DATE_SMA_CLASSIFY" VARCHAR2(100), "RESOLUTION_PLAN_STATUS" VARCHAR2(250), "DATE_FILING_WITH_NCLT" VARCHAR2(250), "DATE_ADDMISSION" VARCHAR2(250), "LOAN_BUYOUT_TAKEOVER" VARCHAR2(200), "DATE_BUYOUT_TAKEOVER" VARCHAR2(200), "WHETHER_CC_OD_FAC" VARCHAR2(200), "AGGREGATE_FUND_BASED_WC_LIMIT" NUMBER, "OF_WHICH_INTRA_CR_LIMIT" VARCHAR2(200), "LIMIT_SANCTIONED_FUNDED" NUMBER, "CASH_CREDIT_OVERDRAFT" NUMBER, "WORKING_CAPITAL_DEMAND_LOAN" NUMBER, "INLAND_BILLS" NUMBER, "PACKING_CREDIT" NUMBER, "EXPORT_BILLS" NUMBER, "TERM_LOAN" NUMBER, "BILLS_DISCONTINUED_DEFRED" NUMBER, "OTHER_FUNDED_OUTSTANDING" NUMBER, "TOTAL_FUNDED_OUTSTANDING" NUMBER, "AMT_ELIGIBLE_NETNG_FUNDEDEXPO" NUMBER, "FUNDED_CREDIT_EXPOSURE" NUMBER, "SECURED_FUNDED_AMT" NUMBER, "LIMIT_SANCTIONED_NON_FUNDED" NUMBER, "LETTER_OF_CREDIT" NUMBER, "GUARANTEES" NUMBER, "ACCEPTANCES" VARCHAR2(250), "FOREIGN_EXCHANGE_CONTRACTS" NUMBER, "INTEREST_RATE_DERIVATIVES" NUMBER, "OTHER_NONFUNDED_OUTSTANDING" NUMBER, "TOTAL_NONFUNDED_OUTSTANDING" NUMBER, "AMT_ELIGIBLE_NETNG_NONFUNDED" NUMBER, "NONFUNDED_CREDIT_EXPOSURE" NUMBER, "TOTAL_LMT_SANCTIONED_BRWR" NUMBER, "TOTAL_AMT_OUTSTANDING" NUMBER, "OF_WHICH_ADD_FIN_CLASIFY" NUMBER, "TOTAL_CREDIT_EXPOSURE" NUMBER, "TOTAL_CREDIT_EXPO_CRM" VARCHAR2(250), "TCE_AS_PRCNT_OF_CAPITAL_FUNDS" VARCHAR2(250), "TOTAL_INVESTMENT_EXPOSURE" NUMBER, "TOTAL_EXPOSURE" NUMBER, "OFTE_FOREIGN_CURRENCY_EXPOSURE" NUMBER, "TOTAL_EXPOSURE_CRM" VARCHAR2(250), "TE_AS_PRCNT_OF_CAPITAL_FUNDS" VARCHAR2(250), "EXPO_OVERSEAS_BRNCH_INDIANBANK" NUMBER, "TOTAL_PROVISIONS_HELD_NPA" NUMBER, "DICGC_ECGC_CGMTMSE_OTHERCLAIMS" NUMBER, "UNSECURED_AMT_OUTSTANDING" NUMBER, "CURRENT_ACCOUNT_BALANCE" NUMBER(11,2), "AMT_PRUDENTIALLY_WRITTEN_OFF" NUMBER, "DATE_PRUDENTIALLY_WRITTEN_OFF" VARCHAR2(200), "WO_THROUGH_SETTLE" VARCHAR2(250), "OTHER_WO" VARCHAR2(250), "TOTAL_WO" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table C_IDEAL_CRILC_SECTION_1_ORG_OLLLD
--------------------------------------------------------

  CREATE TABLE "C_IDEAL_CRILC_SECTION_1_ORG_OLLLD" ("RPT_SR_NO" NUMBER, "PAN" VARCHAR2(250), "CUSTOMER_NAME" VARCHAR2(1000), "LEI" VARCHAR2(250), "CIN" VARCHAR2(250), "BORROWER_GROUP_CODE" VARCHAR2(250), "BORROWER_GROUP_NAME" VARCHAR2(1000), "INDUSTRY_CODE" VARCHAR2(1000), "INDUSTRY_NAME" VARCHAR2(1000), "SECTOR_CODE" VARCHAR2(1000), "BANKING_ARRANGEMENT" VARCHAR2(1000), "LEAD_BANK_NAME" VARCHAR2(1000), "INTERNAL_RATING" VARCHAR2(1000), "EXTERNAL_RATING" VARCHAR2(1000), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "DATE_NPA_CLASSIFY" VARCHAR2(100), "RESTRUCTING_SCHEME_DATE" VARCHAR2(100), "BRWR_CLASIFID_FRAUD_DEFAULT" VARCHAR2(1000), "DATE_CLASS_WILF_DEFAULT" VARCHAR2(100), "WH_CLASS_RFA_FRAUD" VARCHAR2(1000), "DATE_CLASS_RFA_FRAUD" VARCHAR2(100), "NPA_DUE_FOREIGN_COUNTRY" VARCHAR2(20), "SPECIAL_MENTION_ACCOUNTS" VARCHAR2(1000), "DATE_SMA_CLASSIFY" VARCHAR2(100), "RESOLUTION_PLAN_STATUS" VARCHAR2(250), "DATE_FILING_WITH_NCLT" VARCHAR2(250), "DATE_ADDMISSION" VARCHAR2(250), "LOAN_BUYOUT_TAKEOVER" VARCHAR2(200), "DATE_BUYOUT_TAKEOVER" VARCHAR2(200), "WHETHER_CC_OD_FAC" VARCHAR2(200), "AGGREGATE_FUND_BASED_WC_LIMIT" VARCHAR2(200), "OF_WHICH_INTRA_CR_LIMIT" VARCHAR2(200), "LIMIT_SANCTIONED_FUNDED" VARCHAR2(250), "CASH_CREDIT_OVERDRAFT" VARCHAR2(250), "WORKING_CAPITAL_DEMAND_LOAN" VARCHAR2(250), "INLAND_BILLS" VARCHAR2(250), "PACKING_CREDIT" VARCHAR2(250), "EXPORT_BILLS" VARCHAR2(250), "TERM_LOAN" VARCHAR2(250), "BILLS_DISCONTINUED_DEFRED" VARCHAR2(250), "OTHER_FUNDED_OUTSTANDING" VARCHAR2(250), "TOTAL_FUNDED_OUTSTANDING" VARCHAR2(250), "AMT_ELIGIBLE_NETNG_FUNDEDEXPO" VARCHAR2(250), "FUNDED_CREDIT_EXPOSURE" VARCHAR2(250), "SECURED_FUNDED_AMT" VARCHAR2(200), "LIMIT_SANCTIONED_NON_FUNDED" VARCHAR2(250), "LETTER_OF_CREDIT" VARCHAR2(250), "GUARANTEES" VARCHAR2(250), "ACCEPTANCES" VARCHAR2(250), "FOREIGN_EXCHANGE_CONTRACTS" VARCHAR2(250), "INTEREST_RATE_DERIVATIVES" VARCHAR2(250), "OTHER_NONFUNDED_OUTSTANDING" VARCHAR2(250), "TOTAL_NONFUNDED_OUTSTANDING" VARCHAR2(250), "AMT_ELIGIBLE_NETNG_NONFUNDED" VARCHAR2(250), "NONFUNDED_CREDIT_EXPOSURE" VARCHAR2(250), "TOTAL_LMT_SANCTIONED_BRWR" VARCHAR2(250), "TOTAL_AMT_OUTSTANDING" VARCHAR2(250), "OF_WHICH_ADD_FIN_CLASIFY" VARCHAR2(100), "TOTAL_CREDIT_EXPOSURE" VARCHAR2(250), "TOTAL_CREDIT_EXPO_CRM" VARCHAR2(250), "TCE_AS_PRCNT_OF_CAPITAL_FUNDS" VARCHAR2(250), "TOTAL_INVESTMENT_EXPOSURE" VARCHAR2(250), "TOTAL_EXPOSURE" VARCHAR2(250), "OFTE_FOREIGN_CURRENCY_EXPOSURE" VARCHAR2(250), "TOTAL_EXPOSURE_CRM" VARCHAR2(250), "TE_AS_PRCNT_OF_CAPITAL_FUNDS" VARCHAR2(250), "EXPO_OVERSEAS_BRNCH_INDIANBANK" VARCHAR2(250), "TOTAL_PROVISIONS_HELD_NPA" VARCHAR2(100), "DICGC_ECGC_CGMTMSE_OTHERCLAIMS" VARCHAR2(250), "UNSECURED_AMT_OUTSTANDING" VARCHAR2(250), "CURRENT_ACCOUNT_BALANCE" VARCHAR2(250), "AMT_PRUDENTIALLY_WRITTEN_OFF" VARCHAR2(250), "DATE_PRUDENTIALLY_WRITTEN_OFF" VARCHAR2(200), "WO_THROUGH_SETTLE" VARCHAR2(250), "OTHER_WO" VARCHAR2(250), "TOTAL_WO" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250), "WHETHER_PROJECT_FINANCE" VARCHAR2(10), "DATE_OF_FINANCIAL_CLOSURE" VARCHAR2(100), "DATE_OF_ORIGINAL_DCCO" VARCHAR2(100), "WHETHER_CREDIT_EVENT_TRIGGERED" VARCHAR2(10), "DATE_OF_CREDT_EVENT" VARCHAR2(100), "REASON_FOR_CREDIT_EVENT" VARCHAR2(250), "DATE_OF_REVISED_DCCO" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table C_IDEAL_CRILC_SECTION_1_ORG_RENDERED
--------------------------------------------------------

  CREATE TABLE "C_IDEAL_CRILC_SECTION_1_ORG_RENDERED" ("RPT_SR_NO" NUMBER, "PAN" VARCHAR2(250), "CUSTOMER_NAME" VARCHAR2(1000), "LEI" VARCHAR2(250), "CIN" VARCHAR2(250), "BORROWER_GROUP_CODE" VARCHAR2(250), "BORROWER_GROUP_NAME" VARCHAR2(1000), "INDUSTRY_CODE" VARCHAR2(1000), "INDUSTRY_NAME" VARCHAR2(1000), "SECTOR_CODE" VARCHAR2(1000), "BANKING_ARRANGEMENT" VARCHAR2(1000), "LEAD_BANK_NAME" VARCHAR2(1000), "INTERNAL_RATING" VARCHAR2(1000), "EXTERNAL_RATING" VARCHAR2(1000), "WHETHER_PROJECT_FINANCE" VARCHAR2(10), "DATE_OF_FINANCIAL_CLOSURE" VARCHAR2(100), "DATE_OF_ORIGINAL_DCCO" VARCHAR2(100), "WHETHER_CREDIT_EVENT_TRIGGERED" VARCHAR2(10), "DATE_OF_CREDT_EVENT" VARCHAR2(100), "REASON_FOR_CREDIT_EVENT" VARCHAR2(250), "DATE_OF_REVISED_DCCO" VARCHAR2(100), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "DATE_NPA_CLASSIFY" VARCHAR2(100), "RESTRUCTING_SCHEME_DATE" VARCHAR2(100), "BRWR_CLASIFID_FRAUD_DEFAULT" VARCHAR2(1000), "DATE_CLASS_WILF_DEFAULT" VARCHAR2(100), "WH_CLASS_RFA_FRAUD" VARCHAR2(1000), "DATE_CLASS_RFA_FRAUD" VARCHAR2(100), "NPA_DUE_FOREIGN_COUNTRY" VARCHAR2(20), "SPECIAL_MENTION_ACCOUNTS" VARCHAR2(1000), "DATE_SMA_CLASSIFY" VARCHAR2(100), "RESOLUTION_PLAN_STATUS" VARCHAR2(250), "DATE_FILING_WITH_NCLT" VARCHAR2(250), "DATE_ADDMISSION" VARCHAR2(250), "LOAN_BUYOUT_TAKEOVER" VARCHAR2(200), "DATE_BUYOUT_TAKEOVER" VARCHAR2(200), "WHETHER_CC_OD_FAC" VARCHAR2(200), "AGGREGATE_FUND_BASED_WC_LIMIT" VARCHAR2(200), "OF_WHICH_INTRA_CR_LIMIT" VARCHAR2(200), "LIMIT_SANCTIONED_FUNDED" VARCHAR2(250), "CASH_CREDIT_OVERDRAFT" VARCHAR2(250), "WORKING_CAPITAL_DEMAND_LOAN" VARCHAR2(250), "INLAND_BILLS" VARCHAR2(250), "PACKING_CREDIT" VARCHAR2(250), "EXPORT_BILLS" VARCHAR2(250), "TERM_LOAN" VARCHAR2(250), "BILLS_DISCONTINUED_DEFRED" VARCHAR2(250), "OTHER_FUNDED_OUTSTANDING" VARCHAR2(250), "TOTAL_FUNDED_OUTSTANDING" VARCHAR2(250), "AMT_ELIGIBLE_NETNG_FUNDEDEXPO" VARCHAR2(250), "FUNDED_CREDIT_EXPOSURE" VARCHAR2(250), "SECURED_FUNDED_AMT" VARCHAR2(200), "LIMIT_SANCTIONED_NON_FUNDED" VARCHAR2(250), "LETTER_OF_CREDIT" VARCHAR2(250), "GUARANTEES" VARCHAR2(250), "ACCEPTANCES" VARCHAR2(250), "FOREIGN_EXCHANGE_CONTRACTS" VARCHAR2(250), "INTEREST_RATE_DERIVATIVES" VARCHAR2(250), "OTHER_NONFUNDED_OUTSTANDING" VARCHAR2(250), "TOTAL_NONFUNDED_OUTSTANDING" VARCHAR2(250), "AMT_ELIGIBLE_NETNG_NONFUNDED" VARCHAR2(250), "NONFUNDED_CREDIT_EXPOSURE" VARCHAR2(250), "TOTAL_LMT_SANCTIONED_BRWR" VARCHAR2(250), "TOTAL_AMT_OUTSTANDING" VARCHAR2(250), "OF_WHICH_ADD_FIN_CLASIFY" VARCHAR2(100), "TOTAL_CREDIT_EXPOSURE" VARCHAR2(250), "TOTAL_CREDIT_EXPO_CRM" VARCHAR2(250), "TCE_AS_PRCNT_OF_CAPITAL_FUNDS" VARCHAR2(250), "TOTAL_INVESTMENT_EXPOSURE" VARCHAR2(250), "TOTAL_EXPOSURE" VARCHAR2(250), "OFTE_FOREIGN_CURRENCY_EXPOSURE" VARCHAR2(250), "TOTAL_EXPOSURE_CRM" VARCHAR2(250), "TE_AS_PRCNT_OF_CAPITAL_FUNDS" VARCHAR2(250), "EXPO_OVERSEAS_BRNCH_INDIANBANK" VARCHAR2(250), "TOTAL_PROVISIONS_HELD_NPA" VARCHAR2(100), "DICGC_ECGC_CGMTMSE_OTHERCLAIMS" VARCHAR2(250), "UNSECURED_AMT_OUTSTANDING" VARCHAR2(250), "CURRENT_ACCOUNT_BALANCE" VARCHAR2(250), "AMT_PRUDENTIALLY_WRITTEN_OFF" VARCHAR2(250), "DATE_PRUDENTIALLY_WRITTEN_OFF" VARCHAR2(200), "WO_THROUGH_SETTLE" VARCHAR2(250), "OTHER_WO" VARCHAR2(250), "TOTAL_WO" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table C_IDEAL_CRILC_SECTION_2_ORG
--------------------------------------------------------

  CREATE TABLE "C_IDEAL_CRILC_SECTION_2_ORG" ("RPT_SR_NO" VARCHAR2(100), "PAN" VARCHAR2(250), "BORROWER_CUSTOMER_NAME" VARCHAR2(250), "BORROWER_GROUP_CODE" VARCHAR2(250), "GROUP_NAME" VARCHAR2(250), "INDUSTRY_CODE" VARCHAR2(250), "INDUSTRY_NAME" VARCHAR2(250), "BWR_CLSFID_WILFUL" VARCHAR2(100), "DATE_CLASS_WILF_DEFAULT" VARCHAR2(100), "WH_CLASS_RFA_FRAUD" VARCHAR2(1000), "DATE_CLASS_RFA_FRAUD" VARCHAR2(100), "AMOUNT_TECHNI_PRU_WRITOFF" VARCHAR2(250), "DATEWHEN_PRU_TECHNI_WRITTOFF" VARCHAR2(250), "WO_THROUGH_SETTLE" VARCHAR2(250), "OTHER_WO" VARCHAR2(250), "TOTAL_WO" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table C_IDEAL_CRILC_SECTION_2_ORG_BKUP
--------------------------------------------------------

  CREATE TABLE "C_IDEAL_CRILC_SECTION_2_ORG_BKUP" ("RPT_SR_NO" NUMBER, "PAN" VARCHAR2(250), "BORROWER_CUSTOMER_NAME" VARCHAR2(250), "BORROWER_GROUP_CODE" VARCHAR2(250), "GROUP_NAME" VARCHAR2(250), "INDUSTRY_CODE" VARCHAR2(250), "INDUSTRY_NAME" VARCHAR2(250), "BWR_CLSFID_WILFUL" VARCHAR2(100), "DATE_CLASS_WILF_DEFAULT" VARCHAR2(100), "WH_CLASS_RFA_FRAUD" VARCHAR2(1000), "DATE_CLASS_RFA_FRAUD" VARCHAR2(100), "AMOUNT_TECHNI_PRU_WRITOFF" NUMBER(11,2), "DATEWHEN_PRU_TECHNI_WRITTOFF" VARCHAR2(250), "WO_THROUGH_SETTLE" VARCHAR2(250), "OTHER_WO" VARCHAR2(250), "TOTAL_WO" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table C_IDEAL_CRILC_SECTION_2_ORG_RENDERED
--------------------------------------------------------

  CREATE TABLE "C_IDEAL_CRILC_SECTION_2_ORG_RENDERED" ("RPT_SR_NO" VARCHAR2(100), "PAN" VARCHAR2(250), "BORROWER_CUSTOMER_NAME" VARCHAR2(250), "BORROWER_GROUP_CODE" VARCHAR2(250), "GROUP_NAME" VARCHAR2(250), "INDUSTRY_CODE" VARCHAR2(250), "INDUSTRY_NAME" VARCHAR2(250), "BWR_CLSFID_WILFUL" VARCHAR2(100), "DATE_CLASS_WILF_DEFAULT" VARCHAR2(100), "WH_CLASS_RFA_FRAUD" VARCHAR2(1000), "DATE_CLASS_RFA_FRAUD" VARCHAR2(100), "AMOUNT_TECHNI_PRU_WRITOFF" VARCHAR2(250), "DATEWHEN_PRU_TECHNI_WRITTOFF" VARCHAR2(250), "WO_THROUGH_SETTLE" VARCHAR2(250), "OTHER_WO" VARCHAR2(250), "TOTAL_WO" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table C_IDEAL_CRILC_SECTION_3_ORG
--------------------------------------------------------

  CREATE TABLE "C_IDEAL_CRILC_SECTION_3_ORG" ("RPT_SR_NO" NUMBER, "PAN" VARCHAR2(100), "CUSTOMER_NAME" VARCHAR2(1000), "TOTALCREDITSUMDURREPPER" NUMBER, "TOTALDEBITSUMDURREPPER" NUMBER, "BALANCE_IN_CURRENT_ACCOUNT" VARCHAR2(250), "WHETHER_CC_OD_FAC" VARCHAR2(200), "WHETHER_CURR_AC" VARCHAR2(200), "REPORTING_DATE" VARCHAR2(1000));

--------------------------------------------------------
--  DDL for Table C_IDEAL_CRILC_SECTION_3_ORG_BKUP
--------------------------------------------------------

  CREATE TABLE "C_IDEAL_CRILC_SECTION_3_ORG_BKUP" ("RPT_SR_NO" NUMBER, "PAN" VARCHAR2(100), "CUSTOMER_NAME" VARCHAR2(1000), "TOTALCREDITSUMDURREPPER" NUMBER, "TOTALDEBITSUMDURREPPER" NUMBER, "BALANCE_IN_CURRENT_ACCOUNT" NUMBER(11,2), "WHETHER_CC_OD_FAC" VARCHAR2(200), "WHETHER_CURR_AC" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table C_IDEAL_CRILC_SECTION_3_ORG_RENDERED
--------------------------------------------------------

  CREATE TABLE "C_IDEAL_CRILC_SECTION_3_ORG_RENDERED" ("RPT_SR_NO" NUMBER, "PAN" VARCHAR2(100), "CUSTOMER_NAME" VARCHAR2(1000), "TOTALCREDITSUMDURREPPER" NUMBER, "TOTALDEBITSUMDURREPPER" NUMBER, "BALANCE_IN_CURRENT_ACCOUNT" VARCHAR2(250), "WHETHER_CC_OD_FAC" VARCHAR2(200), "WHETHER_CURR_AC" VARCHAR2(200), "REPORTING_DATE" VARCHAR2(1000));

--------------------------------------------------------
--  DDL for Table C_IDEAL_CRILC_SECTION_4_ORG
--------------------------------------------------------

  CREATE TABLE "C_IDEAL_CRILC_SECTION_4_ORG" ("RPT_SR_NO" NUMBER, "PAN" VARCHAR2(250), "BORROWER_NAME" VARCHAR2(250), "TOTAL_EXPOSURE" VARCHAR2(250), "TOTAL_AMT_OTSTNDG_FUND_NONFNDD" VARCHAR2(250), "RSNS_FOR_CTGONGSNON_CRTVE_BWER" VARCHAR2(3000), "NME_OF_DTRS_PRTNRS_SLE_PROPTER" VARCHAR2(250), "DIRECTOR_IDENTIFICATION_NUMBER" VARCHAR2(250), "STATUS" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table C_IDEAL_CRILC_SECTION_4_ORG_BKUP
--------------------------------------------------------

  CREATE TABLE "C_IDEAL_CRILC_SECTION_4_ORG_BKUP" ("RPT_SR_NO" NUMBER, "PAN" VARCHAR2(250), "BORROWER_NAME" VARCHAR2(250), "TOTAL_EXPOSURE" NUMBER(11,2), "TOTAL_AMT_OTSTNDG_FUND_NONFNDD" NUMBER(11,2), "RSNS_FOR_CTGONGSNON_CRTVE_BWER" VARCHAR2(3000), "NME_OF_DTRS_PRTNRS_SLE_PROPTER" VARCHAR2(250), "DIRECTOR_IDENTIFICATION_NUMBER" VARCHAR2(8), "STATUS" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table C_IDEAL_CRILC_SECTION_4_ORG_Rendered
--------------------------------------------------------

  CREATE TABLE "C_IDEAL_CRILC_SECTION_4_ORG_Rendered" ("RPT_SR_NO" NUMBER, "PAN" VARCHAR2(250), "BORROWER_NAME" VARCHAR2(250), "TOTAL_EXPOSURE" VARCHAR2(250), "TOTAL_AMT_OTSTNDG_FUND_NONFNDD" VARCHAR2(250), "RSNS_FOR_CTGONGSNON_CRTVE_BWER" VARCHAR2(3000), "NME_OF_DTRS_PRTNRS_SLE_PROPTER" VARCHAR2(250), "DIRECTOR_IDENTIFICATION_NUMBER" VARCHAR2(250), "STATUS" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table C_VALIDATION_SETTING_M_ORG
--------------------------------------------------------

  CREATE TABLE "C_VALIDATION_SETTING_M_ORG" ("SRNO" NUMBER, "EXCEL_NAME" VARCHAR2(150), "EXCEL_SHEET" VARCHAR2(150), "VAL_TABLE" VARCHAR2(150), "VAL_COLUMN" VARCHAR2(150), "COMPARE_TABLE" VARCHAR2(150), "COMPARE_COLUMN" VARCHAR2(150), "KEY_COLUMN" VARCHAR2(150), "VAL_TYPE" NUMBER);

--------------------------------------------------------
--  DDL for Table DNBS01_ANNEX1
--------------------------------------------------------

  CREATE TABLE "DNBS01_ANNEX1" ("SR_NO" NUMBER, "NATURE_INSTRUMENTS" VARCHAR2(500), "NAME_INSTRUMENTS" VARCHAR2(500), "BOARD_APPROVE_LMT_INSU_X010" NUMBER(10,2), "NAME_CRED_RATE_AGENCY_X020" VARCHAR2(500), "AMOUNT_RATED_X030" NUMBER(10,2), "CURRENT_RATING_X040" VARCHAR2(20), "DATE_RATING_X050" VARCHAR2(500), "DATE_EXPIRY_RATE_X060" VARCHAR2(500), "PREVIOUS_RATING_X070" VARCHAR2(500), "REMARKS_X080" VARCHAR2(1500), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_ANNEX10
--------------------------------------------------------

  CREATE TABLE "DNBS01_ANNEX10" ("SR_NO" NUMBER, "NAME_OF_ENTITY" VARCHAR2(500), "NATURE_OF_INVEST" VARCHAR2(500), "TYPE_OF_INVEST" VARCHAR2(500), "PAN_X010" VARCHAR2(500), "BOOK_VALUE_X020" NUMBER(10,2), "WHET_GROUP_COMP_X030" VARCHAR2(500), "MARKET_VALUE_X040" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_ANNEX11
--------------------------------------------------------

  CREATE TABLE "DNBS01_ANNEX11" ("SR_NO" NUMBER, "NAME_OF_BORROWER" VARCHAR2(500), "PAN_X010" VARCHAR2(500), "TYPE_OF_BORROWER_X020" VARCHAR2(500), "CIN_NUMBER_X030" VARCHAR2(500), "PURPOSE_LOAN_X040" VARCHAR2(500), "DURATION_LOAN_X050" VARCHAR2(500), "TYPE_OF_LOAN_X060" VARCHAR2(500), "TOT_SANC_LOAN_AMT_X070" VARCHAR2(500), "TOT_OUTSTAND_LOAN_AMT_X080" VARCHAR2(500), "DATE_LAST_PAYM_X090" VARCHAR2(500), "DATE_FIRST_DEFUALT_X100" VARCHAR2(500), "STATUS_OF_ACC_X110" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_ANNEX12
--------------------------------------------------------

  CREATE TABLE "DNBS01_ANNEX12" ("SR_NO" NUMBER, "NAME_GROUP_COMP" VARCHAR2(500), "PAN_X010" VARCHAR2(500), "NATURE_RELATIONSHIP_X020" VARCHAR2(500), "WHET_GRP_ASSO_RBI_X030" VARCHAR2(500), "IF_Y_NBFC_CODE_X040" VARCHAR2(500), "ASS_SIZ_MAR31_PREV_YR_X050" NUMBER(10,2), "ASS_SIZ_LASTDAT_REPQU_X060" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_ANNEX13
--------------------------------------------------------

  CREATE TABLE "DNBS01_ANNEX13" ("SR_NO" NUMBER, "BRANCH_NAME_X010" VARCHAR2(500), "BRANCH_ADDRESS_X020" VARCHAR2(500), "CITY_X030" VARCHAR2(500), "STATE_X040" VARCHAR2(500), "DISTRICT_X050" VARCHAR2(500), "OPENING_DATE_X060" VARCHAR2(500), "CLOSING_DATE_X070" VARCHAR2(500), "NO_DEPO_ACCOUNT_X080" NUMBER, "AMOUNT_PUBL_DEPO_X090" NUMBER(10,2), "NO_LOAN_ACCOUNT_X100" NUMBER, "ACC_LOANS_ADV_OUT_X110" NUMBER(10,2), "REMARKS_X120" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_ANNEX2
--------------------------------------------------------

  CREATE TABLE "DNBS01_ANNEX2" ("SR_NO" NUMBER, "NAME" VARCHAR2(500), "TYPE_CAPITAL" VARCHAR2(500), "PAN_X010" VARCHAR2(500), "NO_SHARE_HELD_X020" NUMBER(10,2), "FACE_VALUE_X030" VARCHAR2(500), "PERCENTAGE_SHAREHOLD_X040" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_ANNEX3
--------------------------------------------------------

  CREATE TABLE "DNBS01_ANNEX3" ("SR_NO" NUMBER, "NAME" VARCHAR2(500), "DATE_APPOINTMENT_DIR" VARCHAR2(500), "DIN_NUMBER_X010" VARCHAR2(100), "PAN_X020" VARCHAR2(500), "CONTACT_NO_X030" NUMBER, "EMIAL_ID_X040" VARCHAR2(500), "NAME_OTHER_COMP_X050" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_ANNEX4
--------------------------------------------------------

  CREATE TABLE "DNBS01_ANNEX4" ("SR_NO" NUMBER, "NAME_SUBSCRIBER" VARCHAR2(500), "PAN_X010" VARCHAR2(500), "ISSUE_AMOUNT_X020" NUMBER, "ISSUE_RATE_X030" VARCHAR2(500), "RATING_AGEN_NAME_X040" VARCHAR2(500), "ISSUE_DATE_X050" VARCHAR2(500), "DATE_MATURITY_X060" VARCHAR2(500), "COUPON_RATE_X070" NUMBER(20,4), "AMOUNT_OUTSTAND_X080" NUMBER, "WHET_CALL_OPT_ENABL_X090" VARCHAR2(500), "TYPE_OF_OPTION_X100" VARCHAR2(500), "IF_Y_WHET_CALL_OPT_EXCE_X110" VARCHAR2(500), "DATE_EXERCISE_CALL_X120" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_ANNEX5
--------------------------------------------------------

  CREATE TABLE "DNBS01_ANNEX5" ("SR_NO" NUMBER, "NAME_OF_CORP" VARCHAR2(500), "CIN_NUMBER_X010" VARCHAR2(500), "PAN_X020" VARCHAR2(500), "AMOUNT_X030" NUMBER(10,2), "DATE_DEPOSITE_X040" VARCHAR2(500), "DATE_MATURITY_X050" VARCHAR2(500), "AMOUNT_OUTSTAND_X060" NUMBER(10,2), "WHET_GROUP_COMP_X070" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_ANNEX6
--------------------------------------------------------

  CREATE TABLE "DNBS01_ANNEX6" ("SR_NO" NUMBER, "NAME_OF_SUBSCRIBER" VARCHAR2(500), "PAN_X010" VARCHAR2(500), "ISSUE_AMOUNT_X020" NUMBER(10,2), "ISSUE_RATING_X030" VARCHAR2(500), "RATING_AGE_NAME_X040" VARCHAR2(500), "FACE_VALUE_X050" NUMBER(10,2), "DATE_OF_ISSUE_X060" VARCHAR2(500), "DATE_OF_MATURITY_X070" VARCHAR2(500), "DISCOUNTED_RATE_X080" NUMBER(20,4), "AMOUNT_OUTSTAND_X090" NUMBER(10,2), "STATUS_INSTRUMENT_X100" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_ANNEX7
--------------------------------------------------------

  CREATE TABLE "DNBS01_ANNEX7" ("SR_NO" NUMBER, "NAME_SUBSCRIBER" VARCHAR2(500), "PAN_X010" VARCHAR2(500), "ISSUE_AMOUNT_X020" NUMBER, "ISSUE_RATE_X030" VARCHAR2(500), "RATING_AGEN_NAME_X040" VARCHAR2(500), "ISSUE_DATE_X050" VARCHAR2(500), "DATE_MATURITY_X060" VARCHAR2(500), "COUPON_RATE_X070" NUMBER(20,4), "AMOUNT_OUTSTAND_X080" NUMBER, "WHET_CALL_OPT_ENABL_X090" VARCHAR2(500), "TYPE_OF_OPTION_X100" VARCHAR2(500), "IF_Y_WHET_CALL_OPT_EXCE_X110" VARCHAR2(500), "DATE_EXERCISE_CALL_X120" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_ANNEX8
--------------------------------------------------------

  CREATE TABLE "DNBS01_ANNEX8" ("SR_NO" NUMBER, "NAME_SUBSCRIBER" VARCHAR2(500), "PAN_X010" VARCHAR2(500), "ISSUE_AMOUNT_X020" NUMBER, "ISSUE_RATE_X030" VARCHAR2(500), "RATING_AGEN_NAME_X040" VARCHAR2(500), "ISSUE_DATE_X050" VARCHAR2(500), "DATE_MATURITY_X060" VARCHAR2(500), "COUPON_RATE_X070" NUMBER(20,4), "AMOUNT_OUTSTAND_X080" NUMBER, "WHET_CALL_OPT_ENABL_X090" VARCHAR2(500), "TYPE_OF_OPTION_X100" VARCHAR2(500), "IF_Y_WHET_CALL_OPT_EXCE_X110" VARCHAR2(500), "DATE_EXERCISE_CALL_X120" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_ANNEX9
--------------------------------------------------------

  CREATE TABLE "DNBS01_ANNEX9" ("SR_NO" NUMBER, "NAME_OF_BORROWER" VARCHAR2(500), "PAN_X010" VARCHAR2(500), "TYPE_BORROWER_X020" VARCHAR2(500), "TOT_SANC_LOAN_AMT_X030" NUMBER(10,2), "DISB_LOAN_AMOUNT_X040" NUMBER(10,2), "UN_DISB_LOAN_AMT_X050" NUMBER(10,2), "TOT_PRINC_OUTSTAND_AMT_X060" NUMBER(10,2), "TOT_ACCUR_INTRE_AMT_X070" NUMBER(10,2), "STATUS_ACCOUNT_X080" VARCHAR2(500), "AMOUNT_OUTSTAND_X090" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_FILING
--------------------------------------------------------

  CREATE TABLE "DNBS01_FILING" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_FILING_2
--------------------------------------------------------

  CREATE TABLE "DNBS01_FILING_2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART1
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "AMOUNT_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART10
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART10" ("SR_NO" NUMBER, "PERIOD_DELIQ" VARCHAR2(500), "LOANS_ADV_OUTST_X010" NUMBER(10,2), "HP_LEASE_ASS_X020" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART11
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART11" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "AMT_OUTSTAND_X010" NUMBER(10,2), "MIN_PERC_X020" NUMBER(10,2), "MAX_PERC_X030" NUMBER(10,2), "WEIGHT_AVR_INTRATE_X040" NUMBER(10,2), "ACT_INT_PAID_Q_X050" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART12
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART12" ("SR_NO" NUMBER, "DETAILS" VARCHAR2(500), "BOOK_VAL_LOAN_SECU_X010" NUMBER(10,2), "AMT_LOAN_SECU_X020" NUMBER(10,2), "PROV_HELD_X030" NUMBER(10,2), "GAIN_LOS_SALE_SEC_X040" NUMBER(10,2), "RETAINED_INTER_X050" NUMBER(10,2), "REMARKS" VARCHAR2(500), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART13A_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART13A_LAY1" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "NUM_ACCOUNTS_X010" NUMBER(10,2), "AMT_OUTSTAND_X020" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART13A_LAY2
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART13A_LAY2" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "AMOUNT_X030" NUMBER(20,4), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART13A_LAY3
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART13A_LAY3" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "AMOUNT_X040" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART13_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART13_LAY1" ("SR_NO" NUMBER, "DETAILS" VARCHAR2(500), "NUM_ACCOUNTS_X010" NUMBER(10,2), "FUND_EXPO_X020" NUMBER(10,2), "NON_FUND_EXPO_X030" NUMBER(10,2), "TOTAL_X040" NUMBER(10,2), "IMPAIRED_ACC_X050" NUMBER(10,2), "LOSS_PREV_HELD_X060" NUMBER(10,2), "INT_RATE_MIN_X070" NUMBER(10,2), "INT_RATE_MAX_X080" NUMBER(10,2), "WGHT_AVR_RATE_INT_X090" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART14_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART14_LAY1" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "NO_ACCOUNTS_X010" NUMBER(20,4), "AMT_OUTSTAND_X020" NUMBER(20,4), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART14_LAY2
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART14_LAY2" ("SR_NO" VARCHAR2(20), "NAME_DEPOSITOR_X030" VARCHAR2(500), "AMOUNT_X040" NUMBER(10,2), "DATE_MATURITY_X050" DATE, "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART14_LAY3
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART14_LAY3" ("SR_NO" VARCHAR2(20), "NAME_DEPOSITOR_X060" VARCHAR2(500), "AMOUNT_X070" NUMBER(10,2), "DATE_MATURITY_X080" DATE, "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART14_LAY4
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART14_LAY4" ("SR_NO" VARCHAR2(20), "NAME_DEPOSITOR_X090" VARCHAR2(500), "AMOUNT_X100" NUMBER(10,2), "DATE_MATURITY_X110" DATE, "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART14_LAY5
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART14_LAY5" ("SR_NO" VARCHAR2(20), "NAME_DEPOSITOR_X120" VARCHAR2(500), "AMOUNT_X130" NUMBER(10,2), "DATE_MATURITY_X140" DATE, "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART15_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART15_LAY1" ("SR_NO" NUMBER, "NATURE_GOODS_HIRE" VARCHAR2(500), "NO_ACCOUNTS_X010" NUMBER(10,2), "AMOUNT_X020" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART16_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART16_LAY1" ("SR_NO" NUMBER, "NATURE_EQUIP_LEASE" VARCHAR2(500), "GROSS_LEASE_ASSE_X010" NUMBER(10,2), "ACCUM_DEPR_LEASE_ACC_X020" NUMBER(10,2), "NET_LEASE_ASSET_AMT_X030" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART2
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "AMOUNT_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART3
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART3" ("SR_NO" NUMBER, "ITEMS_OF_INCOME" VARCHAR2(500), "CURRENT_Q_AMT_X010" NUMBER(10,2), "CUM_CUR_Q_AMT_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART4
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART4" ("SR_NO" NUMBER, "ITEM" VARCHAR2(500), "BANKS_X010" NUMBER(10,2), "INSUR_COMP_X020" NUMBER(10,2), "MUTUAL_FUND_COMP_X030" NUMBER(10,2), "PENSION_FUNDS_X040" NUMBER(10,2), "HOUSING_FINAN_COMP_X050" NUMBER(10,2), "OTHER_NBFC_X060" NUMBER(10,2), "OTHER_FINAN_ENTITY_X070" NUMBER(10,2), "INVEST_OVERSE_JVCOMP_X080" NUMBER(10,2), "TOTAL_X090" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART4A_1
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART4A_1" ("SR_NO" NUMBER, "NAME_BANK_NBFC" VARCHAR2(500), "TERM_LOAN_BAL_X010" NUMBER(10,2), "WORK_CAPIT_BAL_X020" NUMBER(10,2), "DEBENT_BAL_X030" NUMBER(10,2), "COMME_PAPER_BAL_X040" NUMBER(10,2), "OTHERS_BAL_X050" NUMBER(10,2), "TOTAL_BAL_X060" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART4A_2
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART4A_2" ("SR_NO" NUMBER, "NAME_BANK_NBFC" VARCHAR2(500), "LETTER_CRED_BAL_X070" NUMBER(10,2), "FINAN_OTHER_GUR_BAL_X080" NUMBER(10,2), "BILLS_REDISC_BAL_X090" NUMBER(10,2), "LEASE_CONTR_BAL_X100" NUMBER(10,2), "FORW_EXCH_CONTR_BAL_X110" NUMBER(10,2), "INTR_RATE_SWAP_BAL_X120" NUMBER(10,2), "OTHER_CONT_LIAB_BAL_X130" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART4B_1
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART4B_1" ("SR_NO" NUMBER, "NAME_BANK_NBFC" VARCHAR2(500), "LOANS_X010" NUMBER(10,2), "EQUITY_X020" NUMBER(10,2), "PREFERENCE_X030" NUMBER(10,2), "DEBENTURE_X040" NUMBER(10,2), "ICD_CPS_X050" NUMBER(10,2), "OTHERS_X060" NUMBER(10,2), "TOTAL_X070" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART4B_2
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART4B_2" ("SR_NO" NUMBER, "NAME_BANK_NBFC" VARCHAR2(500), "LCS_X080" NUMBER(10,2), "GURENTEES_X090" NUMBER(10,2), "OTHERS_X100" NUMBER(10,2), "TOTAL_X110" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART5_1
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART5_1" ("SR_NO" NUMBER, "PAN_X010" VARCHAR2(500), "NAME_GROUP_X020" VARCHAR2(500), "LOANS_X030" NUMBER(10,2), "INVEST_EQUITY_X040" NUMBER(10,2), "INVEST_PREF_SHARES_X050" NUMBER(10,2), "INVEST_DEBENT_X060" NUMBER(10,2), "ICDS_X070" NUMBER(10,2), "CPS_X080" NUMBER(10,2), "OTHERS_X090" NUMBER(10,2), "TOTAL_X100" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART5_2
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART5_2" ("SR_NO" NUMBER, "PAN_X110" VARCHAR2(500), "NAME_GROUP_X120" VARCHAR2(500), "LCS_X130" NUMBER(10,2), "GUARANTEES_X140" NUMBER(10,2), "OTHERS_X150" NUMBER(10,2), "TOTAL_X160" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART6_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART6_LAY1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "OUTSATN_BANLANCE_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART6_LAY2
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART6_LAY2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "OUTSATN_BANLANCE_X020" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART6_LAY3
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART6_LAY3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "OUTSATN_BANLANCE_X030" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART6_LAY4
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART6_LAY4" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "OUTSATN_BANLANCE_X030" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART7
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART7" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "AMOUNT_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART8_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART8_LAY1" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "OUTSTAND_BAL_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART8_LAY2
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART8_LAY2" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "OUTSTAND_BAL_X020" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART9A_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART9A_LAY1" ("SR_NO" NUMBER, "ITEM" VARCHAR2(500), "NUMBER_ACC_X010" NUMBER(10,2), "TOT_ADV_OUTST_FUND_X020" NUMBER(10,2), "NO_ACC_STAND_ADV_Q_X030" NUMBER(10,2), "STAND_ADV_BEGIN_Q_X040" NUMBER(10,2), "NO_ACC_GROSS_NPA_X050" NUMBER(10,2), "GRSS_NPS_BEG_QUR_X060" NUMBER(10,2), "NO_ACC_NEW_ACRE_X070" NUMBER(10,2), "NEW_ACCR_STAN_ADV_X080" NUMBER(10,2), "NO_ACC_UPGRAD_X090" NUMBER(10,2), "UPGRADE_DUR_Q_X100" NUMBER(10,2), "NO_ACC_ACTU_RECOV_X110" NUMBER(10,2), "ACTAUL_RECOVER_X120" NUMBER(10,2), "ACC_WRITEN_OFF_X130" NUMBER(10,2), "WRITEN_OFF_AMT_X140" NUMBER(10,2), "REDU_ADDI_RBI_X150" NUMBER(10,2), "NUMBER_ACC_X160" NUMBER(10,2), "GRSS_NPS_END_QUR_X170" NUMBER(10,2), "STAND_ADVANC_X180" NUMBER(10,2), "SUB_STAND_ADV_X190" NUMBER(10,2), "DOUBT_ADV_X200" NUMBER(10,2), "ULOSS_ADV_X210" NUMBER(10,2), "TOT_LOSS_PREV_HELD_X220" NUMBER(10,2), "CUM_WRITE_OFF_X230" NUMBER(10,2), "CUM_WRITOFF_OUTSTAN_BANK_X240" NUMBER(10,2), "TOT_REST_OUTST_ADV_X250" NUMBER(10,2), "REMARKS_X260" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART9B_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART9B_LAY1" ("SR_NO" NUMBER, "ITEM" VARCHAR2(500), "NUMBER_ACC_X010" NUMBER(10,2), "TOT_ADV_OUTST_X020" NUMBER(10,2), "STAND_ADV_X030" NUMBER(10,2), "SUB_STAND_ADV_X040" NUMBER(10,2), "DOUBT_ADV_X050" NUMBER(10,2), "LOSS_ADV_X060" NUMBER(10,2), "WRITEN_OFF_AMT_X070" NUMBER(10,2), "TOT_REST_OUTST_ADV_X080" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART9C_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART9C_LAY1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "LOANS_ADV_OUTS_INTR_X010" NUMBER(20,4), "PROV_HELD_X020" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART9D_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART9D_LAY1" ("SR_NO" VARCHAR2(500), "QUR_END_LAST_4_Q_X010" VARCHAR2(20), "AMT_NPA_BEG_Q_X020" NUMBER(10,2), "RECOV_EFECT_NPA_Q_X030" NUMBER(10,2), "WRITE_OFF_EFECT_Q_X040" NUMBER(10,2), "ADDI_NPA_Q_X050" NUMBER(10,2), "AMT_NPA_END_Q_X060" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART9E_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART9E_LAY1" ("SR_NO" NUMBER, "REST_LOANS_ADVS" VARCHAR2(500), "ACC_REST_X010" NUMBER(10,2), "OF_WHICH_CDR_X020" NUMBER(10,2), "ACC_RESTR_END_Q_X030" NUMBER(10,2), "OF_WHICH_CDR_X040" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_PART9E_LAY2
--------------------------------------------------------

  CREATE TABLE "DNBS01_PART9E_LAY2" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(500), "AMOUNT_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS01_SIGN
--------------------------------------------------------

  CREATE TABLE "DNBS01_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_ANNEX1
--------------------------------------------------------

  CREATE TABLE "DNBS02_ANNEX1" ("SRNO" NUMBER, "NATURE_INSTRU" VARCHAR2(200), "NAME_INSTRU" VARCHAR2(200), "BOARD_APPR_X010" NUMBER(10,2), "CRED_RAT_AGEN_X020" VARCHAR2(200), "AMT_RAT_X030" NUMBER(10,2), "CURR_RAT_X040" VARCHAR2(200), "DT_RAT_X050" VARCHAR2(200), "DT_EXP_RAT_X060" VARCHAR2(200), "PREV_RAT_X070" VARCHAR2(200), "REMARK_X080" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_ANNEX10
--------------------------------------------------------

  CREATE TABLE "DNBS02_ANNEX10" ("SR_NO" NUMBER, "NAME_ENTITY" VARCHAR2(200), "NAT_INVEST" VARCHAR2(200), "TYP_INVEST" VARCHAR2(200), "PAN_X010" VARCHAR2(10), "BOOK_VAL_X020" NUMBER(10,2), "GRP_CMPN_X030" VARCHAR2(200), "MRKT_VAL_X040" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_ANNEX11
--------------------------------------------------------

  CREATE TABLE "DNBS02_ANNEX11" ("SRNO" NUMBER, "NAME_BORRO" VARCHAR2(200), "PAN_X010" VARCHAR2(10), "TYPE_BORRO_X020" VARCHAR2(200), "CIN_X030" VARCHAR2(200), "PUR_LOAN_X040" VARCHAR2(200), "DUR_LOAN_X050" VARCHAR2(200), "TYP_LOAN_X060" VARCHAR2(200), "TTL_SAN_AMNT_X070" NUMBER(10,2), "TTL_OUT_AMNT_X080" NUMBER(10,2), "DT_LAST_X090" VARCHAR2(200), "DT_FRST_X0100" VARCHAR2(200), "STS_ACC_X0110" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_ANNEX12
--------------------------------------------------------

  CREATE TABLE "DNBS02_ANNEX12" ("SRNO" NUMBER, "NAME_GRP" VARCHAR2(200), "PAN_X010" VARCHAR2(10), "NAT_REL_X020" VARCHAR2(200), "REG_NBFC_X030" VARCHAR2(200), "NBFC_CODE_X040" VARCHAR2(200), "PREV_FINYR_X050" NUMBER(10,2), "LSTDT_REP_X060" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_ANNEX13
--------------------------------------------------------

  CREATE TABLE "DNBS02_ANNEX13" ("SRNO" NUMBER, "BRNCH_NAME_X010" VARCHAR2(200), "BRNC_ADD_X020" VARCHAR2(200), "CITY_X030" VARCHAR2(200), "STAT_X040" VARCHAR2(200), "DIS_X050" VARCHAR2(200), "OP_DT_X060" VARCHAR2(200), "CL_DT_X070" VARCHAR2(200), "NO_DEP_ACC_X080" NUMBER, "NUM_LOAN_ACC_X090" NUMBER, "AMNT_LOAN_X0100" NUMBER(10,2), "REMARK_X0110" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_ANNEX2
--------------------------------------------------------

  CREATE TABLE "DNBS02_ANNEX2" ("SR_NO" VARCHAR2(200), "NAME" VARCHAR2(200), "TYP_CAP" VARCHAR2(200), "PAN_X010" VARCHAR2(10), "NUM_SHARE_X020" NUMBER, "FACE_VAL_X030" NUMBER(10,2), "PER_SHARE_X040" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_ANNEX3
--------------------------------------------------------

  CREATE TABLE "DNBS02_ANNEX3" ("SRNO" NUMBER, "NAME" VARCHAR2(200), "DT_APOINT" VARCHAR2(200), "DIN_X010" VARCHAR2(200), "PAN_X020" VARCHAR2(10), "CONT_NUM_X030" VARCHAR2(200), "EMAIL_X040" VARCHAR2(200), "NAME_OTHR_X050" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_ANNEX4
--------------------------------------------------------

  CREATE TABLE "DNBS02_ANNEX4" ("SRNO" NUMBER, "NAME_SUB" VARCHAR2(200), "PAN_X010" VARCHAR2(10), "ISUE_AMNT_X020" NUMBER(10,2), "ISSUE_RAT_X030" VARCHAR2(100), "RAT_AGENCY_X040" VARCHAR2(200), "ISSUE_DT_X050" VARCHAR2(200), "DT_MAT_X060" VARCHAR2(200), "CPN_RT_X070" NUMBER(20,4), "AMNT_OUT_X080" NUMBER(10,2), "PUT_CALL_X090" VARCHAR2(200), "TYPE_OPTION_X0100" VARCHAR2(200), "CALL_EXCER_X0110" VARCHAR2(200), "DT_EXCER_X0120" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_ANNEX5
--------------------------------------------------------

  CREATE TABLE "DNBS02_ANNEX5" ("SRNO" NUMBER, "NAME_CORP" VARCHAR2(200), "CIN_X010" VARCHAR2(200), "PAN_X020" VARCHAR2(10), "AMNT_X030" NUMBER(10,2), "DT_DEP_X040" VARCHAR2(200), "DT_MAT_X050" VARCHAR2(200), "AMNT_OUT_X060" NUMBER(10,2), "WHTHR_GRP_X070" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_ANNEX6
--------------------------------------------------------

  CREATE TABLE "DNBS02_ANNEX6" ("SRNO" NUMBER, "NAME_SUB" VARCHAR2(200), "PAN_X010" VARCHAR2(10), "ISUE_AMNT_X020" NUMBER(10,2), "FACE_VAL_X030" NUMBER(10,2), "ISUE_RAT_X040" VARCHAR2(200), "RAT_AGRN_X050" VARCHAR2(200), "DT_ISSUE_X060" VARCHAR2(200), "DT_MAT_X070" VARCHAR2(200), "DSCNT_RAT_X080" NUMBER(20,4), "AMNT_OUT_X090" NUMBER(10,2), "STS_INCR_X0100" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_ANNEX7
--------------------------------------------------------

  CREATE TABLE "DNBS02_ANNEX7" ("SRNO" NUMBER, "NAME_SUB" VARCHAR2(200), "PAN_X010" VARCHAR2(10), "ISUE_AMNT_X020" NUMBER(10,2), "ISSUE_RAT_X030" VARCHAR2(200), "RAT_AGENCY_X040" VARCHAR2(200), "ISSUE_DT_X050" VARCHAR2(200), "DT_MAT_X060" VARCHAR2(200), "CPN_RT_X070" NUMBER(20,4), "AMNT_OUT_X080" NUMBER(10,2), "PUT_CALL_X090" VARCHAR2(200), "TYPE_OPTION_X0100" VARCHAR2(200), "CALL_EXCER_X0110" VARCHAR2(200), "DT_EXCER_X0120" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_ANNEX8
--------------------------------------------------------

  CREATE TABLE "DNBS02_ANNEX8" ("SRNO" NUMBER, "NAME_SUB" VARCHAR2(200), "PAN_X010" VARCHAR2(10), "ISUE_AMNT_X020" NUMBER(10,2), "ISSUE_RAT_X030" VARCHAR2(200), "RAT_AGENCY_X040" VARCHAR2(200), "ISSUE_DT_X050" VARCHAR2(200), "DT_MAT_X060" VARCHAR2(200), "CPN_RT_X070" NUMBER(20,4), "AMNT_OUT_X080" NUMBER(10,2), "PUT_CALL_X090" VARCHAR2(200), "TYPE_OPTION_X0100" VARCHAR2(200), "CALL_EXCER_X0110" VARCHAR2(200), "DT_EXCER_X0120" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_ANNEX9
--------------------------------------------------------

  CREATE TABLE "DNBS02_ANNEX9" ("SRNO" NUMBER, "NAME_BORRO" VARCHAR2(200), "PAN_X010" VARCHAR2(10), "TYPE_BORRO_X020" VARCHAR2(200), "SANC_AMNT_X030" NUMBER(10,2), "DIS_LOAN_AMNT_X040" NUMBER(10,2), "UNDIS_LOAN_AMNT_X050" NUMBER(10,2), "TTL_AMNT_X060" NUMBER(10,2), "INTR_AMNT_X070" NUMBER(10,2), "STA_ACC_X080" VARCHAR2(200), "AMNT_OUT_X090" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_FILING
--------------------------------------------------------

  CREATE TABLE "DNBS02_FILING" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_PART1
--------------------------------------------------------

  CREATE TABLE "DNBS02_PART1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "AMOUNT_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_PART2
--------------------------------------------------------

  CREATE TABLE "DNBS02_PART2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "AMOUNT_X010" NUMBER(20,4), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_PART3
--------------------------------------------------------

  CREATE TABLE "DNBS02_PART3" ("SR_NO" NUMBER, "INCOME_ITEM" VARCHAR2(500), "AMOUNT_X010" NUMBER(20,4), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_PART4
--------------------------------------------------------

  CREATE TABLE "DNBS02_PART4" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "AMOUNT_X010" NUMBER(10,2), "REMARK_X020" VARCHAR2(500), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_PART5
--------------------------------------------------------

  CREATE TABLE "DNBS02_PART5" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "BOOK_VAL_X010" NUMBER(10,2), "CONVER_FACT_X020" NUMBER(20,4), "EQUIV_VAL_X030" NUMBER(10,2), "RISK_WGT_X040" NUMBER(20,4), "ADJUST_VAL_X050" NUMBER(10,2), "REMARK_X060" VARCHAR2(500), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_PART5_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS02_PART5_LY2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "NO_TRANSACTION_X070" NUMBER, "BOOK_VAL_X080" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_PART6_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS02_PART6_LY1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "OUTSTANDING_BAL_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_PART6_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS02_PART6_LY2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "OUTSTANDING_BAL_X020" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_PART7
--------------------------------------------------------

  CREATE TABLE "DNBS02_PART7" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(500), "AMOUNT_X010" NUMBER(20,4), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_PART7_A1
--------------------------------------------------------

  CREATE TABLE "DNBS02_PART7_A1" ("SRNO" VARCHAR2(200), "PAN_X010" VARCHAR2(10), "NAME_GRP_X020" VARCHAR2(200), "LOAN_GIV_X030" NUMBER(10,2), "INVS_EQU_X040" NUMBER(10,2), "PREF_SHR_X050" NUMBER(10,2), "INV_DEB_X060" NUMBER(10,2), "ICD_X070" NUMBER(10,2), "CP_X080" NUMBER(10,2), "OTHR_X090" NUMBER(10,2), "TOTAL_X0100" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_PART7_A2
--------------------------------------------------------

  CREATE TABLE "DNBS02_PART7_A2" ("SRNO" VARCHAR2(200), "PAN_X010" VARCHAR2(10), "NAME_GRP_X020" VARCHAR2(200), "LC_X030" NUMBER(10,2), "GUARANT_X040" NUMBER(10,2), "OTHR_X050" NUMBER(10,2), "TOTAL_X060" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_PART8
--------------------------------------------------------

  CREATE TABLE "DNBS02_PART8" ("SR_NO" NUMBER, "ITEM" VARCHAR2(500), "NO_ACC_X010" NUMBER, "TOT_ADV_X020" NUMBER(10,2), "NO_ACC_STANDADV_X030" NUMBER, "STANDADV_X040" NUMBER(10,2), "NO_ACC_GROSSNPA_X050" NUMBER, "GROSSNPA_X060" NUMBER(10,2), "NO_NPA_X070" NUMBER, "NPA_X080" NUMBER(10,2), "NO_UPGRAD_X090" NUMBER, "UPGRAD_X0100" NUMBER(10,2), "NO_ACTUAL_REC_X0110" NUMBER, "ACTUAL_REC_X0120" NUMBER(10,2), "NO_WRITTEOFF_X0130" NUMBER, "WRITTEOFF_X0140" NUMBER(10,2), "REDU_ADDI_X0150" NUMBER(10,2), "NO_ACC_GROSSNPA_X0160" NUMBER, "GROSSNPA_X0170" NUMBER(10,2), "STAN_ADV_X0180" NUMBER(10,2), "SUBSTAN_ADV_X0190" NUMBER(10,2), "DOUT_ADV_X0200" NUMBER(10,2), "LOSS_ADV_X0210" NUMBER(10,2), "TOTALLOSS_PROHD_X0220" NUMBER(10,2), "COMULATIVE_WF_X0230" NUMBER(10,2), "COMULATIVE_WF_AMTAUC_X0240" NUMBER(10,2), "ADV_OUTSTANDING_X0250" NUMBER(10,2), "REMARK_X0260" VARCHAR2(500), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_PART8A
--------------------------------------------------------

  CREATE TABLE "DNBS02_PART8A" ("SR_NO" NUMBER, "DETAILS" VARCHAR2(200), "NO_ACC_X010" NUMBER, "FUNDED_EXP_X020" NUMBER(10,2), "NONFUNDED_EXP_X030" NUMBER(10,2), "TOTAL_X040" NUMBER(10,2), "MIN_X050" NUMBER(10,2), "MAX_X060" NUMBER(10,2), "WGT_AVR_X070" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_PART8B
--------------------------------------------------------

  CREATE TABLE "DNBS02_PART8B" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(500), "NO_AC_X010" NUMBER, "AMT_OUTSTANDING_X020" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_PART8C
--------------------------------------------------------

  CREATE TABLE "DNBS02_PART8C" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(500), "BAL_AMT_X010" NUMBER(20,4), "PROVIHELD_AMT_X020" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_PART9A1
--------------------------------------------------------

  CREATE TABLE "DNBS02_PART9A1" ("SR_NO" VARCHAR2(200), "COMPANY_NM" VARCHAR2(500), "AMOUNT_X050" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_PART9_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS02_PART9_LY1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "BOOK_VAL_X010" NUMBER(10,2), "RISK_WGT_X020" NUMBER(20,4), "ADJ_VAL_X030" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_PART9_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS02_PART9_LY2" ("SR_NO" VARCHAR2(200), "COMPANY_NM" VARCHAR2(500), "AMOUNT_X040" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_SCOP_QUE
--------------------------------------------------------

  CREATE TABLE "DNBS02_SCOP_QUE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS02_SIGN
--------------------------------------------------------

  CREATE TABLE "DNBS02_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_ANNEX1
--------------------------------------------------------

  CREATE TABLE "DNBS03_ANNEX1" ("SRNO" VARCHAR2(100), "SECURITY_NAME" VARCHAR2(200), "AMOUNT_X010" NUMBER(10,2), "INTEREST_COLL_DT_X020" VARCHAR2(200), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_ANNEX2
--------------------------------------------------------

  CREATE TABLE "DNBS03_ANNEX2" ("SRNO" VARCHAR2(100), "NAME_BANK" VARCHAR2(200), "ADR_BNK_X030" VARCHAR2(200), "PRI_AMT_X040" NUMBER(10,2), "INTRST_AMT_X050" NUMBER(10,2), "TOTAL_X060" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_ANNEX3
--------------------------------------------------------

  CREATE TABLE "DNBS03_ANNEX3" ("SRNO" NUMBER, "NAME_BANK" VARCHAR2(200), "NAME_BRNCH_X070" VARCHAR2(200), "ADDRESS_X080" VARCHAR2(100), "REMARK_X090" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_ANNEX4
--------------------------------------------------------

  CREATE TABLE "DNBS03_ANNEX4" ("SRNO" NUMBER, "NAME_BANK" VARCHAR2(200), "DT_FR0M_X0100" VARCHAR2(200), "DT_TO_X0110" VARCHAR2(100), "AMT_REQ_X0120" NUMBER(10,2), "ASST_MAIN_X0130" NUMBER(10,2), "NO_DAY_X0140" NUMBER(10,2), "SHORTFALL_X0150" NUMBER(10,2), "RT_PENL_X0160" NUMBER(20,4), "PENL_INTRST_X0170" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_FILING
--------------------------------------------------------

  CREATE TABLE "DNBS03_FILING" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART10
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART10" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "AMOUNT_X010" VARCHAR2(200), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART11
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART11" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "AMOUNT_X010" VARCHAR2(200), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART1_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART1_LY1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "AMOUNT_X010" NUMBER(10,2), "REMARK_X020" VARCHAR2(200), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART1_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART1_LY2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "AMOUNT_X030" NUMBER(10,2), "REMARK_X040" VARCHAR2(200), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART1_LY3
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART1_LY3" ("SR_NO" NUMBER, "INSTITUTION" VARCHAR2(200), "AMOUNT_X050" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART1_LY4
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART1_LY4" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "AMOUNT_X060" NUMBER(20,4), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART2
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(400), "AMOUNT_X010" NUMBER(10,2), "REMARK_X020" VARCHAR2(200), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART3_A
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART3_A" ("SR_NO" VARCHAR2(200), "ASSET_TYPE" VARCHAR2(200), "AMOUNT_X050" NUMBER(10,2), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table DNBS03_PART3_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART3_LY1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "BOOKVAL_X010" NUMBER(10,2), "RISKWGT_X020" NUMBER(20,4), "ADJUSTEDVAL_X030" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART3_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART3_LY2" ("SR_NO" VARCHAR2(200), "ASSET_TYPE" VARCHAR2(200), "AMOUNT_X040" NUMBER(10,2), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table DNBS03_PART4_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART4_LY1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "BOOKVAL_X010" NUMBER(10,2), "CONVERSIONFACTOR_X020" NUMBER(20,4), "EQUIVALENTVAL_X030" NUMBER(10,2), "RISKWGT_X040" NUMBER(20,4), "ADJUSTEDVAL_X050" NUMBER(10,2), "REMARK__X060" VARCHAR2(200), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART4_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART4_LY2" ("SR_NO" NUMBER, "INTEREST_RATE" VARCHAR2(500), "TRANS_NO_X070" NUMBER, "BOOKVAL_X080" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART5
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART5" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE_X010" NUMBER(20,4), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART6
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART6" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "VALUE_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART6_A
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART6_A" ("SRNO" VARCHAR2(100), "PAN_X020" VARCHAR2(10), "NAME_SUB_X030" VARCHAR2(200), "NATURE_CMP_X040" VARCHAR2(200), "TYPE_X050" VARCHAR2(200), "OUT_AMNT_X060" NUMBER(10,2), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table DNBS03_PART6_B
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART6_B" ("SRNO" VARCHAR2(100), "PAN_X070" VARCHAR2(10), "NAME_SUB_X080" VARCHAR2(200), "NATURE_CMP_X090" VARCHAR2(200), "OUT_AMNT_X0100" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART6_C
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART6_C" ("SRNO" VARCHAR2(100), "PAN_X0110" VARCHAR2(10), "NAME_OTRCMP_X0120" VARCHAR2(200), "TYPE_X0130" VARCHAR2(200), "OUT_AMNT_X0140" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART7
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART7" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "VALUE_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART7_A
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART7_A" ("SRNO" VARCHAR2(100), "PAN_X020" VARCHAR2(10), "NAME_OFCMP_X030" VARCHAR2(200), "OUT_LOAN_X040" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART7_B
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART7_B" ("SRNO" VARCHAR2(100), "PAN_X050" VARCHAR2(10), "NAME_OFCMP_X060" VARCHAR2(200), "OUT_LOAN_X070" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART7_C
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART7_C" ("SRNO" VARCHAR2(100), "PAN_X080" VARCHAR2(10), "NAME_OFCMP_X090" VARCHAR2(200), "OUT_LOAN_X01OO" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART7_D
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART7_D" ("SRNO" VARCHAR2(100), "PAN_X0110" VARCHAR2(10), "NAME_OFCMP_X0120" VARCHAR2(200), "OUT_LOAN_X013O" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART7_E
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART7_E" ("SRNO" VARCHAR2(100), "PAN_X0140" VARCHAR2(10), "NAME_OFCMP_X0150" VARCHAR2(200), "OUT_LOAN_X0160" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART7_F
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART7_F" ("SRNO" VARCHAR2(100), "PAN_X0170" VARCHAR2(10), "NAME_OFCMP_X0180" VARCHAR2(200), "OUT_LOAN_X0190" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART8
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART8" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "AMOUNT_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_PART9
--------------------------------------------------------

  CREATE TABLE "DNBS03_PART9" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "NO_CASES_X010" NUMBER, "AMOUNT_X020" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_SCOP_QUE
--------------------------------------------------------

  CREATE TABLE "DNBS03_SCOP_QUE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS03_SIGN
--------------------------------------------------------

  CREATE TABLE "DNBS03_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS05_FILING_INFO
--------------------------------------------------------

  CREATE TABLE "DNBS05_FILING_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS05_PARTA
--------------------------------------------------------

  CREATE TABLE "DNBS05_PARTA" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS05_SIGN
--------------------------------------------------------

  CREATE TABLE "DNBS05_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART1
--------------------------------------------------------

  CREATE TABLE "DNBS06PART1" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(600), "VALUE" NUMBER(20,4), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART10_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS06PART10_LAY1" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(400), "AMNT_X010" NUMBER(10,2), "CODE" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART10_LAY2
--------------------------------------------------------

  CREATE TABLE "DNBS06PART10_LAY2" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(400), "AMNT_X020" NUMBER(10,2), "CODE" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART11_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS06PART11_LAY1" ("SR_NO" VARCHAR2(200), "NAME_BRNC" VARCHAR2(400), "DT_OPEN_X010" VARCHAR2(20), "ADRS_X020" VARCHAR2(400), "CITY_X030" VARCHAR2(400), "DIS_X040" VARCHAR2(400), "STATE_X050" VARCHAR2(400), "AMNT_DEP_X060" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART11_LAY2
--------------------------------------------------------

  CREATE TABLE "DNBS06PART11_LAY2" ("SR_NO" NUMBER, "NM_SUB" VARCHAR2(400), "ADRS_X070" VARCHAR2(400), "NM_DIR_X080" VARCHAR2(400), "BUS_ACT_X090" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART12_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS06PART12_LAY1" ("SR_NO" NUMBER, "NM_BRNCH" VARCHAR2(400), "ADRS_X010" VARCHAR2(400), "DT_OPN_X020" VARCHAR2(400), "REF_NO_X030" VARCHAR2(400), "DT_COMMUN_X040" VARCHAR2(400), "REMARK_X050" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART12_LAY2
--------------------------------------------------------

  CREATE TABLE "DNBS06PART12_LAY2" ("SR_NO" NUMBER, "NM_BRNCH" VARCHAR2(400), "ADRS_X060" VARCHAR2(400), "DT_PUB_X070" VARCHAR2(400), "DT_CLS_X080" VARCHAR2(400), "REF_NO_X090" VARCHAR2(400), "DT_COMM_X0100" VARCHAR2(400), "REMARK_X0110" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART2
--------------------------------------------------------

  CREATE TABLE "DNBS06PART2" ("SR_NO" NUMBER, "NAME_OF_SCHEME" VARCHAR2(400), "AMNT_OF_INV_X010" VARCHAR2(400), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART3_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS06PART3_LAY1" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(400), "NUM_OF_CERT_OUT_X10" NUMBER(10,2), "AMOUNT_X20" NUMBER(10,4), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART3_LAY2
--------------------------------------------------------

  CREATE TABLE "DNBS06PART3_LAY2" ("SR_NO" NUMBER, "PERIOD" VARCHAR2(400), "NUM_OF_CERT_OUT_X030" NUMBER(10,2), "TOTAL_AMNT_DEPOSIT_X040" NUMBER(10,2), "NUM_OF_CERT_OUT_X050" NUMBER(10,2), "TOTAL_AMNT_DEPOSIT_X060" NUMBER(10,2), "NUM_OF_CERT_OUT_X070" NUMBER(10,2), "TOTAL_AMNT_DEPOSIT_X080" NUMBER(10,2), "NUM_OF_CERT_OUT_X090" NUMBER(10,2), "TOTAL_AMNT_DEPOSIT_X100" NUMBER(10,2), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART3_LAY3
--------------------------------------------------------

  CREATE TABLE "DNBS06PART3_LAY3" ("SR_NO" NUMBER, "PERIOD" VARCHAR2(400), "RT_OF_FOUR_INT_X110" NUMBER(10,2), "ACC_PRI_X120" NUMBER(10,2), "ACC_AFT_X130" NUMBER(10,2), "RT_OF_EIGHT_INT_X140" NUMBER(10,2), "RT_OF_TEN_INT_X150" NUMBER(10,2), "RT_OF_TEN_INT_ABV_X160" NUMBER(10,2), "TOTAL_X170" NUMBER(10,2), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART3_LAY4
--------------------------------------------------------

  CREATE TABLE "DNBS06PART3_LAY4" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(400), "NUM_CERT_OUT_X180" NUMBER(10,2), "FACE_VAL_X190" NUMBER(10,2), "TOT_AMNT_DEP_X200" NUMBER(10,2), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART3_LAY5
--------------------------------------------------------

  CREATE TABLE "DNBS06PART3_LAY5" ("SR_NO" NUMBER, "CERTI_NO" VARCHAR2(400), "RSN_NON_X0210" VARCHAR2(400), "STP_TKN_X0220" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART4
--------------------------------------------------------

  CREATE TABLE "DNBS06PART4" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(400), "NO_OF_ACC_X010" NUMBER(10,2), "AMNT_X020" NUMBER(10,2), "CODE" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART5_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS06PART5_LAY1" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(400), "AMNT_X010" NUMBER(10,2), "CODE" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART5_LAY10
--------------------------------------------------------

  CREATE TABLE "DNBS06PART5_LAY10" ("SR_NO" VARCHAR2(400), "CMP_NAME" VARCHAR2(400), "AMNT_X090" NUMBER(10,2), "CODE" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART5_LAY11
--------------------------------------------------------

  CREATE TABLE "DNBS06PART5_LAY11" ("SR_NO" VARCHAR2(400), "CMP_NAME" VARCHAR2(400), "AMNT_X0100" NUMBER(10,2), "CODE" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART5_LAY2
--------------------------------------------------------

  CREATE TABLE "DNBS06PART5_LAY2" ("SR_NO" VARCHAR2(400), "CMP_NAME" VARCHAR2(400), "AMNT_X020" NUMBER(10,2), "CODE" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART5_LAY4
--------------------------------------------------------

  CREATE TABLE "DNBS06PART5_LAY4" ("SR_NO" VARCHAR2(400), "CMP_NAME" VARCHAR2(400), "AMNT_X030" NUMBER(10,2), "CODE" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART5_LAY5
--------------------------------------------------------

  CREATE TABLE "DNBS06PART5_LAY5" ("SR_NO" VARCHAR2(400), "CMP_NAME" VARCHAR2(400), "AMNT_X040" NUMBER(10,2), "CODE" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART5_LAY6
--------------------------------------------------------

  CREATE TABLE "DNBS06PART5_LAY6" ("SR_NO" VARCHAR2(400), "CMP_NAME" VARCHAR2(400), "AMNT_X050" NUMBER(10,2), "CODE" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART5_LAY7
--------------------------------------------------------

  CREATE TABLE "DNBS06PART5_LAY7" ("SR_NO" VARCHAR2(400), "CMP_NAME" VARCHAR2(400), "AMNT_X060" NUMBER(10,2), "CODE" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART5_LAY8
--------------------------------------------------------

  CREATE TABLE "DNBS06PART5_LAY8" ("SR_NO" VARCHAR2(400), "CMP_NAME" VARCHAR2(400), "AMNT_X070" NUMBER(10,2), "CODE" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART5_LAY9
--------------------------------------------------------

  CREATE TABLE "DNBS06PART5_LAY9" ("SR_NO" VARCHAR2(400), "CMP_NAME" VARCHAR2(400), "AMNT_X080" NUMBER(10,2), "CODE" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART6
--------------------------------------------------------

  CREATE TABLE "DNBS06PART6" ("SR_NO" VARCHAR2(400), "PARTICULARS" VARCHAR2(400), "PRIOR_COMM_X010" NUMBER(10,2), "AFT_COMM_X020" NUMBER(10,2), "CODE" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART7_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS06PART7_LAY1" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(400), "AMNT_X010" NUMBER(10,2), "CODE" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART7_LAY2
--------------------------------------------------------

  CREATE TABLE "DNBS06PART7_LAY2" ("SR_NO" NUMBER, "CMP_NAME" VARCHAR2(400), "AMNT_X020" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART8_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS06PART8_LAY1" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(400), "AMNT_X010" NUMBER(10,2), "CODE" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART8_LAY2
--------------------------------------------------------

  CREATE TABLE "DNBS06PART8_LAY2" ("SR_NO" NUMBER, "CMP_NAME" VARCHAR2(400), "DIR_NAME" VARCHAR2(400), "ADD_X020" VARCHAR2(400), "OUT_CRD_EXP_X030" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART9_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS06PART9_LAY1" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(400), "AMNT_X010" NUMBER(10,2), "CODE" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06PART9_LAY2
--------------------------------------------------------

  CREATE TABLE "DNBS06PART9_LAY2" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(400), "VAL_X020" VARCHAR2(20), "CODE" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06_ANNEX1
--------------------------------------------------------

  CREATE TABLE "DNBS06_ANNEX1" ("SR_NO" VARCHAR2(400), "NM_SEC" VARCHAR2(400), "AMNT_X010" NUMBER(10,2), "INTRST_DTONE_X020" VARCHAR2(400), "INTRST_DTTWO_X030" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06_ANNEX2
--------------------------------------------------------

  CREATE TABLE "DNBS06_ANNEX2" ("SR_NO" VARCHAR2(400), "NM_BANK" VARCHAR2(400), "ADRS_X040" VARCHAR2(400), "AMNT_X050" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06_ANNEX3
--------------------------------------------------------

  CREATE TABLE "DNBS06_ANNEX3" ("SR_NO" NUMBER, "NM_BANK" VARCHAR2(400), "NM_BRNCH_X060" VARCHAR2(400), "ADRS_X070" VARCHAR2(400), "REMARK_X080" VARCHAR2(400), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06_ANNEX4
--------------------------------------------------------

  CREATE TABLE "DNBS06_ANNEX4" ("SR_NO" NUMBER, "DT_FRM_X090" VARCHAR2(400), "DT_TO_X0100" VARCHAR2(400), "ASSET_REQ_X0110" NUMBER, "ASSET_ACT_X0120" NUMBER, "NO_DAY_X0130" NUMBER, "ST_FALL_X0140" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06_ANNEX5
--------------------------------------------------------

  CREATE TABLE "DNBS06_ANNEX5" ("SR_NO" NUMBER, "NM_SCHM" VARCHAR2(400), "AMNT_X0150" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06_AUTH_SIGN1
--------------------------------------------------------

  CREATE TABLE "DNBS06_AUTH_SIGN1" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06_FILEINFO1
--------------------------------------------------------

  CREATE TABLE "DNBS06_FILEINFO1" ("SR_NO" NUMBER, "DESCRPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06_PROF_DT1
--------------------------------------------------------

  CREATE TABLE "DNBS06_PROF_DT1" ("SRNO" NUMBER, "NAME" VARCHAR2(200), "TYP_CAP" VARCHAR2(200), "PAN_X010" VARCHAR2(200), "NUM_SHR_X020" VARCHAR2(200), "AMNT_X030" NUMBER(20,2), "PER_SHR_X040" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06_PROF_DT2
--------------------------------------------------------

  CREATE TABLE "DNBS06_PROF_DT2" ("SRNO" NUMBER, "NAME" VARCHAR2(200), "DT_APOI" VARCHAR2(20), "DIN_X050" NUMBER, "PAN_X060" VARCHAR2(200), "DESIG_X070" VARCHAR2(200), "ADD_X080" VARCHAR2(200), "CON_NUM_X090" VARCHAR2(200), "EMAIL_ID_X0100" VARCHAR2(200), "PER_EQUT_X0110" NUMBER(20,4), "NM_CMP_X0120" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS06_PROF_DT3
--------------------------------------------------------

  CREATE TABLE "DNBS06_PROF_DT3" ("SRNO" NUMBER, "NAME" VARCHAR2(200), "DESIGN_X130" VARCHAR2(200), "ADRS_X140" VARCHAR2(200), "CON_NUM_X0150" VARCHAR2(200), "NAME_CMP_X0160" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_ANNEX1
--------------------------------------------------------

  CREATE TABLE "DNBS07_ANNEX1" ("SRNO" NUMBER, "NTR_INVST" VARCHAR2(200), "NAME_INSTR" VARCHAR2(200), "BOARD_LIMIT_X010" NUMBER(10,2), "NAME_CRED_X020" VARCHAR2(200), "AMNT_RATED_X030" NUMBER(10,2), "CUR_RAT_X040" VARCHAR2(200), "DT_RAT_X050" VARCHAR2(200), "DT_EXP_X060" VARCHAR2(200), "PREV_RAT_X070" VARCHAR2(200), "REMARK_X080" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_ANNEX10
--------------------------------------------------------

  CREATE TABLE "DNBS07_ANNEX10" ("NAME_GRP" VARCHAR2(200), "PAN_X010" VARCHAR2(10), "NTR_REL_X020" VARCHAR2(200), "WTR_GRP_X030" VARCHAR2(200), "NBFC_X040" VARCHAR2(200), "ASST_MRC_X050" NUMBER(10,2), "ASST_LST_X060" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_ANNEX11
--------------------------------------------------------

  CREATE TABLE "DNBS07_ANNEX11" ("SR_NO" NUMBER, "BRNCH_NM_X010" VARCHAR2(200), "BRNC_ADRS_X020" VARCHAR2(200), "CITY_X030" VARCHAR2(200), "STATE_X040" VARCHAR2(200), "DIS_X050" VARCHAR2(200), "OPN_DT_X060" VARCHAR2(200), "CLS_DT_X070" VARCHAR2(200), "NO_DEP_X080" NUMBER, "ACNT_DEP_X090" NUMBER(10,2), "NO_LOAN_X0100" NUMBER, "AMNT_LOAN_X0110" NUMBER(10,2), "REMARK_X0120" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_ANNEX2
--------------------------------------------------------

  CREATE TABLE "DNBS07_ANNEX2" ("NAME" VARCHAR2(200), "TYPE_CAP" VARCHAR2(200), "PAN_X010" VARCHAR2(10), "NUM_SHR_X020" NUMBER, "FACE_VAL_X030" NUMBER(10,2), "PER_SHAR_X040" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_ANNEX3
--------------------------------------------------------

  CREATE TABLE "DNBS07_ANNEX3" ("SRNO" NUMBER, "NAME" VARCHAR2(200), "DT_APOIN" VARCHAR2(200), "DIN_X010" VARCHAR2(200), "PAN_X020" VARCHAR2(10), "CONT_NUM_X030" VARCHAR2(200), "EMAIL_X040" VARCHAR2(200), "NM_CMP_X050" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_ANNEX4
--------------------------------------------------------

  CREATE TABLE "DNBS07_ANNEX4" ("SRNO" NUMBER, "NAME_SUB" VARCHAR2(200), "PAN_X010" VARCHAR2(10), "ISSU_AMNT_X020" NUMBER(10,2), "ISSU_RAT_X030" VARCHAR2(10), "RAT_AGN_X040" VARCHAR2(200), "ISSU_DT_X050" VARCHAR2(200), "DT_MAT_X060" VARCHAR2(200), "COUPN_RAT_X070" NUMBER(10,2), "AMNT_OUT_X080" NUMBER(10,2), "WTR_CALL_X090" VARCHAR2(200), "TYP_OPT_X0100" VARCHAR2(200), "WTHR_CALL_X0110" VARCHAR2(200), "DT_EXER_X0120" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_ANNEX5
--------------------------------------------------------

  CREATE TABLE "DNBS07_ANNEX5" ("SRNO" NUMBER, "NAME_CORP" VARCHAR2(200), "CIN_X010" VARCHAR2(100), "PAN_X020" VARCHAR2(10), "AMNT_X030" NUMBER(10,2), "DT_DEP_X040" VARCHAR2(200), "DT_MAT_X050" VARCHAR2(200), "AMNT_OUT_X060" NUMBER(10,2), "WTR_CMPN_X070" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_ANNEX6
--------------------------------------------------------

  CREATE TABLE "DNBS07_ANNEX6" ("SRNO" NUMBER, "NAME_SUB" VARCHAR2(200), "PAN_X010" VARCHAR2(10), "ISSU_AMNT_X020" NUMBER(10,2), "ISSU_RAT_X030" VARCHAR2(200), "RAT_AGEN_X040" VARCHAR2(200), "FC_VAL_X050" NUMBER(10,2), "DT_ISSUE_X060" VARCHAR2(200), "DT_MAT_X070" VARCHAR2(200), "DSCNT_RT_X080" NUMBER(20,4), "AMNT_OUT_X090" NUMBER(10,2), "STS_INSR_X0100" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_ANNEX7
--------------------------------------------------------

  CREATE TABLE "DNBS07_ANNEX7" ("SRNO" NUMBER, "NAME_SUB" VARCHAR2(200), "PAN_X010" VARCHAR2(10), "ISSU_AMNT_X020" NUMBER(10,2), "ISSU_RAT_X030" VARCHAR2(200), "RAT_AGEN_X040" VARCHAR2(200), "ISSU_DT_X050" VARCHAR2(200), "DT_MAT_X060" VARCHAR2(200), "COUPN_RT_X070" NUMBER(10,2), "AMNT_OUT_X080" NUMBER(10,2), "WTR_CALL_X090" VARCHAR2(200), "TYP_OPTN_X0100" VARCHAR2(200), "WTHR_CALLPUT_X0110" VARCHAR2(200), "DT_EXER_X0120" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_ANNEX8
--------------------------------------------------------

  CREATE TABLE "DNBS07_ANNEX8" ("SRNO" NUMBER, "NAME_SUB" VARCHAR2(200), "PAN_X010" VARCHAR2(10), "ISSU_AMNT_X020" NUMBER(10,2), "ISSU_RAT_X030" VARCHAR2(200), "RAT_AGEN_X040" VARCHAR2(200), "ISSU_DT_X050" VARCHAR2(200), "DT_MAT_X060" VARCHAR2(200), "COUPN_RT_X070" NUMBER(10,2), "AMNT_OUT_X080" NUMBER(10,2), "WTR_CALL_X090" VARCHAR2(200), "TYP_OPTN_X0100" VARCHAR2(200), "WTHR_CALLPUT_X0110" VARCHAR2(200), "DT_EXER_X0120" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_ANNEX9
--------------------------------------------------------

  CREATE TABLE "DNBS07_ANNEX9" ("NAME_ENT" VARCHAR2(200), "NAT_INV" VARCHAR2(200), "TYP_INV" VARCHAR2(200), "PAN_X010" VARCHAR2(10), "BK_VAL_X020" NUMBER(10,2), "WTR_GRP_X030" VARCHAR2(200), "MRKT_VAL_X040" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_FILING
--------------------------------------------------------

  CREATE TABLE "DNBS07_FILING" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART10
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART10" ("SRNO" NUMBER, "CASE_BORROWER" VARCHAR2(200), "DT_ACQUI_X010" VARCHAR2(200), "AQUIRED_FROM_X020" VARCHAR2(200), "COST_AQUI_X030" NUMBER(10,2), "MEASURE_X040" VARCHAR2(200), "TRST_SCHM_X050" VARCHAR2(200), "DT_TRNSF_X060" VARCHAR2(200), "AMNT_SR_X070" NUMBER(10,2), "SR_RDM_X080" NUMBER(10,2), "SR_OUT_X090" NUMBER(10,2), "NET_ASSET_X0100" NUMBER(10,2), "REC_RAT_X0110" VARCHAR2(200), "NAME_RAT_X0120" VARCHAR2(200), "PUR_AQUI_X0130" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART11
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART11" ("SRNO" NUMBER, "TRST_NAME" VARCHAR2(200), "CASE_BORROWER" VARCHAR2(200), "DT_AQUI_X010" VARCHAR2(200), "AQUIR_FRM_X020" VARCHAR2(200), "COST_AQUI_X030" NUMBER(10,2), "MEASURE_X040" VARCHAR2(200), "DT_TRNSF_X050" VARCHAR2(200), "AMNT_SR_X060" VARCHAR2(200), "SR_RDM_X070" NUMBER(10,2), "SR_OUT_X080" NUMBER(10,2), "NET_ASSET_X090" NUMBER(10,2), "REC_RAT_X0100" NUMBER(10,2), "NAME_RAT_X0110" VARCHAR2(200), "PUR_AQUI_X0120" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART12
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART12" ("SRNO" NUMBER, "TRST_NAME" VARCHAR2(200), "NAME_BORROWER" VARCHAR2(200), "SRISSUE_TOTVAL_X010" NUMBER(10,2), "SRREDEM_TOTVAL_X020" NUMBER(10,2), "TOTUPSIDE_X030" NUMBER(10,2), "TOTWRITEOF_X040" NUMBER(10,2), "TOTPROVISION_X050" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART13
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART13" ("SRNO" VARCHAR2(200), "NAME_BANK" VARCHAR2(200), "MODE_AQUI_X010" VARCHAR2(200), "BK_VAL_X020" NUMBER(10,2), "CASH_X030" NUMBER(10,2), "BOND_X040" NUMBER(10,2), "SRS_X050" NUMBER(10,2), "SHRS_ARC_X060" NUMBER(20,4), "SR_INST_X070" NUMBER(20,4), "TTL_AMNT_X080" NUMBER(10,2), "OUT_X090" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART14
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART14" ("SRNO" NUMBER, "BORROWER_NAME" VARCHAR2(200), "DT_AQUI_X010" VARCHAR2(200), "AQUI_FRM_X020" VARCHAR2(200), "EXIST_SECAQUI_X030" NUMBER(10,2), "PERBR_BAL_X040" NUMBER(20,4), "PERBR_POST_X050" NUMBER(20,4), "AMNT_REQ_X060" NUMBER(10,2), "TTL_DEBT_X070" NUMBER(10,2), "MD_SETL_X080" NUMBER, "DT_AQUI_X090" VARCHAR2(200), "EXTN_REA_X0100" NUMBER(10,2), "OUT_BAL_X0110" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART15
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART15" ("SRNO" NUMBER, "NAME_BORR" VARCHAR2(200), "TTL_DBT_X010" NUMBER(10,2), "DBT_CNV_X020" NUMBER(10,2), "PRESHR_BORR_X030" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART16
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART16" ("SRNO" NUMBER, "NAME_BORR" VARCHAR2(200), "DT_AQUI_X010" VARCHAR2(200), "DT_CHNG_X020" VARCHAR2(200), "CHNG_MNG_X030" VARCHAR2(200), "AMNT_OSBK_X040" NUMBER(10,2), "BR_TTL_X050" NUMBER(10,2), "NOSEC_CRED_X060" NUMBER(10,2), "TTL_SR_X070" NUMBER(10,2), "AMNT_SR_X080" NUMBER(10,2), "PER_NINE_X090" NUMBER(20,4), "SEL_LEND_X0100" NUMBER(20,4), "RSN_TK_X0110" VARCHAR2(200), "DT_REP_X0120" VARCHAR2(200), "HIST_REC_X0130" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART17
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART17" ("SRNO" NUMBER, "NAME_SCHEME" VARCHAR2(200), "TRST_NAME" VARCHAR2(200), "DT_CHNG_X010" VARCHAR2(200), "DT_AQUI_X020" NUMBER(10,2), "FV_SR_X030" NUMBER(10,2), "EXP_INC_X040" VARCHAR2(200), "SR_RAT_X050" VARCHAR2(200), "DT_RAT_X060" VARCHAR2(200), "MST_RAT_X070" VARCHAR2(200), "DT_SND__X080" VARCHAR2(200), "SND_RAT_X090" VARCHAR2(200), "DT_TRD_X0100" VARCHAR2(200), "TRD_RAT_X0110" VARCHAR2(200), "NT_SRISSUE_X0120" NUMBER(10,2), "DT_NAV_X0130" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART18
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART18" ("SRNO" NUMBER, "NAME_BORR" VARCHAR2(200), "DT_ACQUI_X010" VARCHAR2(200), "ACQUI_FRM_X020" VARCHAR2(200), "COST_ACQ_X030" NUMBER(10,2), "MEASURE_X040" VARCHAR2(200), "TRST_NAME_X050" VARCHAR2(200), "DT_TRNSF_X060" VARCHAR2(200), "AMNT_SR_X070" NUMBER(10,2), "SR_RDM_X080" NUMBER(10,2), "SR_OUT_X090" NUMBER(10,2), "NET_ASSET_X0100" VARCHAR2(200), "REC_RAT_X0110" VARCHAR2(200), "NAME_RAT_X0120" VARCHAR2(200), "YLD_ARCSR_X0130" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART19
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART19" ("SRNO" NUMBER, "TRST_SCHM" VARCHAR2(200), "DT_ACQUI_X010" VARCHAR2(200), "ACQUI_FRM_X020" VARCHAR2(200), "COST_ACQ_X030" NUMBER(10,2), "TRST_NM_X040" VARCHAR2(200), "DT_TRAN_X050" VARCHAR2(200), "DT_EXT_X060" VARCHAR2(200), "DT_EXP_X070" VARCHAR2(200), "AMNT_SR_X080" NUMBER(10,2), "SR_RDM_X090" NUMBER(10,2), "SR_OUT_X0100" NUMBER(10,2), "NT_ASSET_X0110" NUMBER(10,2), "REC_RAT_X0120" VARCHAR2(200), "NAME_RAT_X0130" VARCHAR2(200), "RSN_DELAY_X0140" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART1_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART1_LY1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "AMOUNT_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART1_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART1_LY2" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(500), "AMOUNT_X020" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART2
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "AMOUNT_X010" NUMBER(10,2), "REMARK_X020" VARCHAR2(500), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART3
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART3" ("SR_NO" NUMBER, "INCOME_ITEM" VARCHAR2(500), "CURRENT_QTR_AMT_X010" NUMBER(10,2), "CUMULATIVE_QTR_X020" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART4
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART4" ("SR_NO" NUMBER, "NAME_BANK" VARCHAR2(100), "TERM_LOAN_X010" NUMBER(10,2), "WORK_CAP_X020" NUMBER(10,2), "DEB_BAL_X030" NUMBER(10,2), "COMM_BAL_X040" NUMBER(10,2), "LOAN_BAL_X050" NUMBER(10,2), "OTHR_BAL_X060" NUMBER(10,2), "NO_DAY_X070" NUMBER, "TOTAL_BAL_X080" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART4_1
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART4_1" ("SR_NO" NUMBER, "NAME_BANK" VARCHAR2(100), "LTR_CRDT_X090" NUMBER(10,2), "FIN_GAURN_X0100" NUMBER(10,2), "BILL_REDIBAL_X0110" NUMBER(10,2), "LEASE_CONTR_X0120" NUMBER(10,2), "FORWRD_EXCNG_X0130" NUMBER(10,2), "INTRST_RT_X0140" NUMBER(10,2), "OTR_CONTIGNT_X0150" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART5
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART5" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(500), "AMOUNT_X010" NUMBER(10,2), "REMARK_X020" VARCHAR2(500), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART6
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART6" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "BK_VAL_X010" NUMBER(10,2), "RISK_WGT_X020" NUMBER(20,4), "ADJUST_VAL_X030" NUMBER(10,2), "REMARK_X040" VARCHAR2(500), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART7
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART7" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(500), "PREVIOUS_QTR_X010" NUMBER(10,2), "POSITION_QTR_X020" NUMBER(10,2), "TOTAL_QTR_X030" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART8A
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART8A" ("SR_NO" NUMBER, "TRST_NAME" VARCHAR2(100), "AMNT_SEC_X010" NUMBER(10,2), "SRS_ISSUE_X020" NUMBER(10,2), "DT_ISSUE_X030" VARCHAR2(100), "NAV_SRLWREND_X040" NUMBER(10,2), "NAV_SRUPRREND_X050" NUMBER(10,2), "NAV_ARC_X060" NUMBER(10,2), "SR_RDMARC_X070" NUMBER(10,2), "SR_RDMAQB_X080" NUMBER(10,2), "OUT_SRS_X090" NUMBER(10,2), "SRS_ISSUE_X0100" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART8_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART8_LY1" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(500), "AMOUNT_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART8_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART8_LY2" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(500), "PREVIOUS_QTR_X020" NUMBER(20,4), "POSITION_QTR_X030" NUMBER(20,4), "TOTAL_QTR_X040" NUMBER(20,4), "NM_TOP_3SR_X050" VARCHAR2(500), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART9_1
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART9_1" ("SR_NO" VARCHAR2(100), "FIN_YR" VARCHAR2(200), "VAL_SRSISSUE_X0140" NUMBER(10,2), "VAL_SRSRDM_X0150" NUMBER(10,2), "ARC_X0160" NUMBER(10,2), "QIB_FII_X0170" NUMBER(10,2), "SELR_BNK_X0180" NUMBER(10,2), "BAL_OUT_X0190" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART9_2
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART9_2" ("SR_NO" NUMBER, "FIN_YR" VARCHAR2(200), "NUM_ASTREQ_X0200" NUMBER, "BK_VALASTREQ_X0210" NUMBER(10,2), "VAL_ASST_X0220" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART9_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART9_LY1" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(500), "PREVIOUS_QTR_X010" NUMBER(10,2), "POSITION_QTR_X020" NUMBER(10,2), "TOTAL_QTR_X030" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_PART9_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS07_PART9_LY2" ("SR_NO" VARCHAR2(200), "FINANCIAL_YEAR" VARCHAR2(100), "ASSET_VAL_X040" NUMBER(10,2), "LESS_1_X050" NUMBER(10,2), "YEAR1_2_X060" NUMBER(10,2), "YEAR2_8_X070" NUMBER(10,2), "MORE_8_X080" NUMBER(10,2), "TOTAL_X090" NUMBER(10,2), "ARC_X0100" NUMBER(10,2), "QIB_X0110" NUMBER(10,2), "SELLER_BANK_X0120" NUMBER(10,2), "BAL_OUTST_X0130" NUMBER(10,2), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table DNBS07_SCOP_QUE
--------------------------------------------------------

  CREATE TABLE "DNBS07_SCOP_QUE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS07_SIGN
--------------------------------------------------------

  CREATE TABLE "DNBS07_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_ACANNEXCIC_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS10_ACANNEXCIC_LY1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE_X010" NUMBER(10,2), "REMARK_X020" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_ACANNEXCIC_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS10_ACANNEXCIC_LY2" ("SR_NO" NUMBER, "NAME_ENTITY" VARCHAR2(500), "PAN_X030" VARCHAR2(200), "NAT_REL_X040" VARCHAR2(200), "COR_NBFC_X050" VARCHAR2(200), "NBFC_CODE_X060" NUMBER, "PREV_FINYR_X070" NUMBER(10,2), "REP_FINYR_X080" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_ACCICMAINS_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS10_ACCICMAINS_LY1" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(200), "DETAIL_X010" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_ACCICMAINS_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS10_ACCICMAINS_LY2" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(600), "DETAIL_X020" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_ACCICMAINS_LY3
--------------------------------------------------------

  CREATE TABLE "DNBS10_ACCICMAINS_LY3" ("SR_NO" NUMBER, "DETAILS_X030" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_FILING
--------------------------------------------------------

  CREATE TABLE "DNBS10_FILING" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_MAINSACARC_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS10_MAINSACARC_LY1" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(500), "DETAILS_X010" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_MAINSACARC_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS10_MAINSACARC_LY2" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(600), "DETAILS_X020" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_MAINSACARC_LY3
--------------------------------------------------------

  CREATE TABLE "DNBS10_MAINSACARC_LY3" ("SR_NO" NUMBER, "DETAILS_X030" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_MAINSACOTHNBFC_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS10_MAINSACOTHNBFC_LY1" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(600), "DETAILS_X010" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_MAINSACOTHNBFC_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS10_MAINSACOTHNBFC_LY2" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(600), "DETAILS_X020" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_MAINSACOTHNBFC_LY3
--------------------------------------------------------

  CREATE TABLE "DNBS10_MAINSACOTHNBFC_LY3" ("SR_NO" NUMBER, "DETAILS_X030" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_MAINSACP2P_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS10_MAINSACP2P_LY1" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(500), "DETAILS_X010" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_MAINSACP2P_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS10_MAINSACP2P_LY2" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(600), "DETAILS_X020" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_MAINSACP2P_LY3
--------------------------------------------------------

  CREATE TABLE "DNBS10_MAINSACP2P_LY3" ("SR_NO" NUMBER, "DETAILS_X030" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_SACANNEXOTHNBFC_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS10_SACANNEXOTHNBFC_LY1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE_X010" NUMBER(10,2), "REMARK_X020" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_SACANNEXOTHNBFC_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS10_SACANNEXOTHNBFC_LY2" ("SR_NO" NUMBER, "NAME_ENTITY" VARCHAR2(500), "PAN_X030" VARCHAR2(200), "NAT_REL_X040" VARCHAR2(200), "COR_NBFC_X050" VARCHAR2(200), "NBFC_CODE_X060" NUMBER, "PREV_FINYR_X070" NUMBER(10,2), "REP_FINYR_X080" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_SACANNEXOTHNBFC_P1LY1
--------------------------------------------------------

  CREATE TABLE "DNBS10_SACANNEXOTHNBFC_P1LY1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "VALUE_X090" NUMBER(20,4), "REMARK_X0100" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_SACANNEXOTHNBFC_P1LY2
--------------------------------------------------------

  CREATE TABLE "DNBS10_SACANNEXOTHNBFC_P1LY2" ("SR_NO" NUMBER, "INCOME_ITEM" VARCHAR2(500), "VALUE_X0110" NUMBER(20,4), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_SACNNEXARC_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS10_SACNNEXARC_LY1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE_X010" NUMBER(10,2), "REMARK_X020" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_SACNNEXARC_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS10_SACNNEXARC_LY2" ("SR_NO" NUMBER, "NAME_ENTITY" VARCHAR2(500), "PAN_X030" VARCHAR2(200), "NAT_REL_X040" VARCHAR2(200), "COR_NBFC_X050" VARCHAR2(200), "NBFC_CODE_X060" VARCHAR2(200), "PREV_FINYR_X070" NUMBER(10,2), "REP_FINYR_X080" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_SACNNEXP2P_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS10_SACNNEXP2P_LY1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE_X010" NUMBER(10,2), "REMARK_X020" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_SACNNEXP2P_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS10_SACNNEXP2P_LY2" ("SR_NO" NUMBER, "NAME_ENTITY" VARCHAR2(500), "PAN_X030" VARCHAR2(200), "NAT_REL_X040" VARCHAR2(200), "COR_NBFC_X050" VARCHAR2(200), "NBFC_CODE_X060" NUMBER, "PREV_FINYR_X070" NUMBER(10,2), "REP_FINYR_X080" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS10_SCOP_QUE
--------------------------------------------------------

  CREATE TABLE "DNBS10_SCOP_QUE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_ANNEX1
--------------------------------------------------------

  CREATE TABLE "DNBS11_ANNEX1" ("SR_NO" NUMBER, "NATURE_INSTR" VARCHAR2(100), "NM_INSTRUMENT" VARCHAR2(100), "BOARD_APP_X010" NUMBER(10,2), "NM_CREDIT_X020" VARCHAR2(200), "AMT_RATED_X030" NUMBER(10,2), "CUR_RATING_X040" VARCHAR2(100), "DT_RATING_X050" VARCHAR2(100), "DT_EXP_RT_X060" VARCHAR2(100), "PREV_RAT_X070" VARCHAR2(100), "REMARK_X080" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_ANNEX10_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS11_ANNEX10_LY1" ("SR_NO" NUMBER, "NM_SCRIP_X010" VARCHAR2(100), "NM_CMP_X020" VARCHAR2(100), "GRP_REL_X030" VARCHAR2(100), "CAT_INSTR_X040" VARCHAR2(100), "NO_SHR_X050" NUMBER, "PRI_UNIT_X060" NUMBER(10,2), "BK_VAL_X070" NUMBER(10,2), "MRKT_QUART_X080" NUMBER(10,2), "MARKT_VAL_X090" NUMBER(10,2), "APPREC_X0100" NUMBER(10,2), "PROVISION_X0110" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_ANNEX10_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS11_ANNEX10_LY2" ("SR_NO" NUMBER, "NM_SCRIP_X0120" VARCHAR2(100), "NM_CMP_X0130" VARCHAR2(100), "TYP_GRP_X0140" VARCHAR2(100), "CAT_INSTR_X0150" VARCHAR2(100), "NO_SHR_X0160" NUMBER, "PRI_UNIT_X0170" VARCHAR2(100), "BK_VAL_X0180" NUMBER(10,2), "COST_X0190" VARCHAR2(100), "TOTAL_VAL_X0200" NUMBER(10,2), "DT_BAL_X0210" VARCHAR2(100), "PROVISION_X0220" VARCHAR2(100), "SH_FALL_X0230" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_ANNEX10_LY3
--------------------------------------------------------

  CREATE TABLE "DNBS11_ANNEX10_LY3" ("SR_NO" NUMBER, "NM_SCRIP_X0240" VARCHAR2(100), "NM_CMP_X0250" VARCHAR2(100), "TYP_GRP_X0260" VARCHAR2(100), "CAT_INSTR_X0270" VARCHAR2(100), "NO_SHR_X0280" NUMBER, "PRI_UNIT_X0290" VARCHAR2(100), "BK_VAL_X0300" NUMBER(10,2), "DT_VAL_X0310" VARCHAR2(100), "TOTAL_VAL_X0320" NUMBER(10,2), "PROVI_X0330" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_ANNEX11
--------------------------------------------------------

  CREATE TABLE "DNBS11_ANNEX11" ("SR_NO" NUMBER, "NM_BORR" VARCHAR2(100), "PAN_X010" VARCHAR2(10), "TYP_BORR_X020" VARCHAR2(100), "CIN_X030" VARCHAR2(100), "PUR_LOAN_X040" VARCHAR2(100), "DUR_LOAN_X050" VARCHAR2(100), "TYO_LOAN_X060" VARCHAR2(100), "TOTAL_SAN_X070" NUMBER(10,2), "TOTAL_OUT_X080" NUMBER(10,2), "DT_PAY_X090" VARCHAR2(100), "DT_DEF_X0100" VARCHAR2(100), "ECL_X0110" NUMBER(10,2), "STS_AMNT_X0120" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_ANNEX12
--------------------------------------------------------

  CREATE TABLE "DNBS11_ANNEX12" ("SR_NO" NUMBER, "NAME_CMP" VARCHAR2(100), "PAN_X010" VARCHAR2(10), "CIN_X020" VARCHAR2(100), "NAT_REL_X030" VARCHAR2(100), "CMPRG_NBFC_X040" VARCHAR2(100), "NBFC_CD_X050" VARCHAR2(100), "MARPREV_FYR_X060" NUMBER(10,2), "LSTDT_REP_X070" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_ANNEX13
--------------------------------------------------------

  CREATE TABLE "DNBS11_ANNEX13" ("SR_NO" NUMBER, "BRNCH_NM_X010" VARCHAR2(100), "BRNCH_ADRS_X020" VARCHAR2(10), "CITY_X030" VARCHAR2(100), "STATE_X040" VARCHAR2(100), "DISTRICT_X050" VARCHAR2(100), "OPN_DT_X060" VARCHAR2(100), "CLS_DT_X070" VARCHAR2(100), "NUMDEP_ACC_X080" NUMBER, "AMNPUB_DEP_X090" NUMBER(10,2), "NUMLOAN_ACC_X0100" NUMBER, "AMNTLOAN_OUT_X0110" NUMBER(10,2), "REMARK_X0120" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_ANNEX2
--------------------------------------------------------

  CREATE TABLE "DNBS11_ANNEX2" ("SR_NO" NUMBER, "NAME" VARCHAR2(100), "TYP_CAP" VARCHAR2(100), "PAN_X010" VARCHAR2(10), "NUM_SHR_X020" NUMBER(10,2), "FC_VAL_X030" NUMBER(10,2), "PER_SHR_X040" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_ANNEX3
--------------------------------------------------------

  CREATE TABLE "DNBS11_ANNEX3" ("SR_NO" NUMBER, "NAME" VARCHAR2(100), "DT_APPOIN" VARCHAR2(100), "DIN_X010" VARCHAR2(100), "DESIGN_X020" VARCHAR2(100), "PAN_X030" VARCHAR2(10), "CON_NUM_X040" NUMBER, "EMAIL_ID_X050" VARCHAR2(100), "NM_CMP_X060" VARCHAR2(100), "DT_REP_X070" VARCHAR2(100), "DT_RESIGN_X080" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_ANNEX4
--------------------------------------------------------

  CREATE TABLE "DNBS11_ANNEX4" ("SR_NO" NUMBER, "NAME_SUB" VARCHAR2(100), "PAN_X010" VARCHAR2(10), "ISUE_AMNT_X020" NUMBER(10,2), "ISUE_RAT_X030" VARCHAR2(100), "RAT_AGEN_X040" VARCHAR2(100), "ISUE_DT_X050" VARCHAR2(100), "DT_MAT_X060" VARCHAR2(100), "CPN_RT_X070" VARCHAR2(200), "AMNT_OUT_X080" NUMBER(10,2), "WTR_ENBL_X090" VARCHAR2(100), "TYP_CAP_X0100" VARCHAR2(100), "PUT_EXER_X0110" VARCHAR2(100), "DT_EXER_X0120" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_ANNEX5
--------------------------------------------------------

  CREATE TABLE "DNBS11_ANNEX5" ("SR_NO" NUMBER, "NAME_COR" VARCHAR2(100), "CIN_X010" VARCHAR2(100), "PAN_X020" VARCHAR2(10), "AMNT_X030" NUMBER(10,2), "DT_DEP_X040" VARCHAR2(100), "DT_MAT_X050" VARCHAR2(100), "AMNT_OUT_X060" NUMBER(10,2), "WTR_GRP_X070" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_ANNEX6
--------------------------------------------------------

  CREATE TABLE "DNBS11_ANNEX6" ("SR_NO" NUMBER, "NAME_SUB" VARCHAR2(100), "PAN_X010" VARCHAR2(10), "ISSU_AMNT_X020" NUMBER(10,2), "ISSUE_RAT_X030" VARCHAR2(100), "RT_AGEN_X040" VARCHAR2(100), "FC_VAL_X050" NUMBER(10,2), "DT_ISUE_X060" VARCHAR2(100), "DT_MAT_X070" VARCHAR2(100), "DIS_RT_X080" NUMBER(20,4), "AMNT_OUT_X090" NUMBER(10,2), "STS_INSTR_X0100" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_ANNEX7
--------------------------------------------------------

  CREATE TABLE "DNBS11_ANNEX7" ("SR_NO" NUMBER, "NAME_SUB" VARCHAR2(100), "PAN_X010" VARCHAR2(10), "ISSU_AMNT_X020" NUMBER(10,2), "ISSUE_RAT_X030" VARCHAR2(100), "RT_AGEN_X040" VARCHAR2(100), "ISSUE_DT_X050" VARCHAR2(100), "DT_MAT_X060" VARCHAR2(100), "CPN_RT_X070" NUMBER(20,4), "AMNT_OUT_X080" NUMBER(10,2), "WTR_CALL_X090" VARCHAR2(100), "TYP_OPTN_X0100" VARCHAR2(100), "PUT_EXER_X0110" VARCHAR2(100), "DT_EXER_X0120" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_ANNEX8
--------------------------------------------------------

  CREATE TABLE "DNBS11_ANNEX8" ("SR_NO" NUMBER, "NAME_SUB" VARCHAR2(100), "PAN_X010" VARCHAR2(10), "ISSU_AMNT_X020" NUMBER(10,2), "ISSUE_RAT_X030" VARCHAR2(100), "RT_AGEN_X040" VARCHAR2(100), "ISSUE_DT_X050" VARCHAR2(100), "DT_MAT_X060" VARCHAR2(100), "CPN_RT_X070" NUMBER(20,4), "AMNT_OUT_X080" NUMBER(10,2), "WTR_CALL_X090" VARCHAR2(100), "TYP_OPTN_X0100" VARCHAR2(100), "PUT_EXER_X0110" VARCHAR2(100), "DT_EXER_X0120" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_ANNEX9
--------------------------------------------------------

  CREATE TABLE "DNBS11_ANNEX9" ("SR_NO" NUMBER, "NAME_BORR" VARCHAR2(100), "PAN_X010" VARCHAR2(10), "TYPE_BORR_X020" VARCHAR2(100), "BORR_GRO_X030" VARCHAR2(100), "DT_DIS_X040" VARCHAR2(100), "DT_ORI_X050" VARCHAR2(100), "SANC_AMT_X060" NUMBER(10,2), "DISB_AMT_X070" NUMBER(10,2), "UNDIS_AMT_X080" NUMBER(10,2), "ANNU_INT_X090" NUMBER(20,4), "PRIN_AMT_X0100" NUMBER(10,2), "ACC_AMT_X0110" NUMBER(10,2), "LEV_LOAN_X0120" NUMBER(10,2), "LEV_AFTERLOAN_X0130" NUMBER(10,2), "STA_ACC_X0140" VARCHAR2(100), "AMT_OUT_X0150" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_FILING
--------------------------------------------------------

  CREATE TABLE "DNBS11_FILING" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART1
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "AMOUNT_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART10
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART10" ("SR_NO" NUMBER, "DELINQUE_PERIOD" VARCHAR2(200), "LOAN_ADV_INT_X010" NUMBER(10,2), "HP_LEAS_INT_X020" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART11
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART11" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(200), "AMT_OUT_X010" NUMBER(10,2), "MIN_X020" NUMBER(10,2), "MAX_X030" NUMBER(10,2), "WGT_AVR_X040" NUMBER(10,2), "ACTUAL_INT_X050" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART12
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART12" ("SR_NO" NUMBER, "DETAILS" VARCHAR2(200), "BK_VAL_LN_X010" NUMBER(10,2), "AMT_LAON_X020" NUMBER(10,2), "PROVISION_HLD_X030" NUMBER(10,2), "GAIN_LOSS_X040" NUMBER(10,2), "RETAINED_INT_X050" NUMBER(10,2), "REMARK_X060" VARCHAR2(500), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART13
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART13" ("SR_NO" NUMBER, "DETAILS" VARCHAR2(200), "NO_ACC_X010" NUMBER(10,2), "FUNDED_EXP_X020" NUMBER(10,2), "NONFUNDED_EXP_X030" NUMBER(10,2), "TOTAL_X040" NUMBER(10,2), "IMPAIRE_AMT_X050" NUMBER(10,2), "LOSS_PROV_X060" NUMBER(10,2), "MIN_X070" NUMBER(10,2), "MAX_X080" NUMBER(10,2), "WGT_AVR_X090" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART2
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "AMOUNT_X010" NUMBER(10,2), "REMARK_X020" VARCHAR2(500), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART3
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART3" ("SR_NO" NUMBER, "INCOME_ITEMS" VARCHAR2(500), "CRNT_QTR_AMNT_X010" NUMBER(10,2), "CUMULATIVE_QTR_AMNT_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART4
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART4" ("SR_NO" NUMBER, "ITEM" VARCHAR2(500), "BANK_X010" NUMBER(10,2), "INSURANCE_COM_X020" NUMBER(10,2), "MUTUAL_FUND_X030" NUMBER(10,2), "PENSION_FUND_X040" NUMBER(10,2), "HOUSING_FINANCE_X050" NUMBER(10,2), "OTH_NBFC_X060" NUMBER(10,2), "OTH_FINANCIAL_X070" NUMBER(10,2), "INVEST_COMP_X080" NUMBER(10,2), "TOTAL_X090" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART4_A1
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART4_A1" ("SR_NO" NUMBER, "BANK_NAME" VARCHAR2(500), "TERM_LOAN_X010" NUMBER(10,2), "WORKING_CAP_X020" NUMBER(10,2), "DEBENTURE_BAL_X030" NUMBER(10,2), "COMMERCIAL_BAL_X040" NUMBER(10,2), "ICD_BAL_X050" NUMBER(10,2), "OTH_BAL_X060" NUMBER(10,2), "TOTAL_X070" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART4_A2
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART4_A2" ("SR_NO" NUMBER, "BANK_NAME" VARCHAR2(500), "CREDIT_BAL_X080" NUMBER(10,2), "FINANCIAL_BAL_X090" NUMBER(10,2), "BILL_REDIS_BAL_X100" NUMBER(10,2), "LEASE_CON_BAL_X110" NUMBER(10,2), "FORW_EX_BAL_X120" NUMBER(10,2), "INTEREST_RT_BAL_X130" NUMBER(10,2), "OTH_CONTINGENT_X140" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART5
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART5" ("SR_NO" VARCHAR2(200), "PAN_X010" VARCHAR2(10), "CIN_X020" VARCHAR2(50), "NM_GRP_X030" VARCHAR2(100), "REL_CIC_X040" VARCHAR2(100), "TYP_ENT_X050" VARCHAR2(100), "NTR_BUS_X060" VARCHAR2(100), "NM_STOCK_X070" VARCHAR2(100), "NM_CIC_X080" NUMBER, "NM_KMP_X090" NUMBER, "MX_EXP_X0100" NUMBER(10,2), "LOANS_X0110" NUMBER(10,2), "EQUITY_X0120" NUMBER(10,2), "PREF_X0130" NUMBER(10,2), "DEB_X0140" NUMBER(10,2), "ICD_X0150" NUMBER(10,2), "CPS_X0160" NUMBER(10,2), "OTRS_X0170" NUMBER(10,2), "TOTAL_X0180" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART5_A1
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART5_A1" ("SR_NO" VARCHAR2(100), "PAN_X010" VARCHAR2(10), "IDENTIFICATION_NO_X020" VARCHAR2(50), "NAME_GRP_X030" VARCHAR2(100), "REL_CIC_X040" VARCHAR2(100), "TYP_ENT_X050" VARCHAR2(100), "NTR_BUS_X060" VARCHAR2(100), "LC_AMT_X070" NUMBER(10,2), "GUARANTEES_AMT_X080" NUMBER(10,2), "OTH_AMT_X090" NUMBER(10,2), "TOTAL_AMT_X0100" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART6_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART6_LY1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "OUTSTANDING_BAL_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART6_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART6_LY2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "OUTSTANDING_BAL_X020" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART6_LY3
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART6_LY3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "OUTSTANDING_BAL_X030" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART6_LY4
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART6_LY4" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "OUTSTANDING_BAL_X040" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART7
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART7" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "AMOUNT_X040" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART8_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART8_LY1" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "OUTSTANDING_BAL_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART8_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART8_LY2" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "OUTSTANDING_BAL_X020" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART9
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART9" ("SR_NO" NUMBER, "ITEM" VARCHAR2(500), "NO_ACC_X010" NUMBER, "TOT_ADVANCE_X020" NUMBER(10,2), "NO_ACC_STA_ADV_X030" NUMBER, "STANDARD_ADV_X040" NUMBER(10,2), "NO_ACC_NPA_X050" NUMBER, "GROSS_NPA_QTR_X060" NUMBER(10,2), "NO_ACC_ACCRETION_X070" NUMBER, "ACCRESTION_NPA_X080" NUMBER(10,2), "NO_ACC_UPGRADED_X090" NUMBER, "UPGRADATION_QTR_X100" NUMBER(10,2), "NO_RECOVERIESACC_X110" NUMBER, "RECOVERIES_X120" NUMBER(10,2), "NO_WRITTEOFFACC_X130" NUMBER, "WRITEOFF_AMT_X140" NUMBER(10,2), "REDUCTION_ADD_X150" NUMBER(10,2), "NO_ACC_GROSSNPA_X160" NUMBER, "GROSS_NPA_X170" NUMBER(10,2), "STAND_ADV_X180" NUMBER(10,2), "SUB_STAND_X190" NUMBER(10,2), "DOUT_ADV_X200" NUMBER(10,2), "LOSS_ADV_X210" NUMBER(10,2), "TOT_LOSS_X220" NUMBER(10,2), "COMULA_WRIT_X230" NUMBER(10,2), "OUTSTA_BK_X240" NUMBER(10,2), "ADV_OUTSTA_X250" NUMBER(10,2), "REMARK_X260" VARCHAR2(500), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART9A
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART9A" ("SR_NO" NUMBER, "ITEM" VARCHAR2(500), "NO_ACC_X010" NUMBER, "TOT_ADVANCE_X020" NUMBER(10,2), "STAND_ADV_X030" NUMBER(10,2), "SUB_STAND_X040" NUMBER(10,2), "DOUT_ADV_X050" NUMBER(10,2), "LOSS_ADV_X060" NUMBER(10,2), "WRITEOFF_AMT_X070" NUMBER(10,2), "TOT_OUTS_X080" NUMBER(10,2), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART9B
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART9B" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "LOAN_ADV_INTRE_X010" NUMBER(20,4), "PROVISION_HELD_X020" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART9C
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART9C" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "LAST_FOURQTR_X010" VARCHAR2(200), "AMT_NPA_X020" NUMBER(10,2), "RECOVRIES_X030" NUMBER(10,2), "WRITEOFF_X040" NUMBER(10,2), "ADDI_NPA_X050" NUMBER(10,2), "AMT_NPA_X060" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART9D_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART9D_LY1" ("SR_NO" NUMBER, "LOAN_ADVANCE" VARCHAR2(200), "ACC_RESTRUCTUR_X010" NUMBER(10,2), "CDR_X020" NUMBER(10,2), "ACC_REST_QTR_X030" NUMBER(10,2), "CDR_X040" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_PART9D_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS11_PART9D_LY2" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(200), "AMT_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_SCOP_QUE
--------------------------------------------------------

  CREATE TABLE "DNBS11_SCOP_QUE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS11_SIGN
--------------------------------------------------------

  CREATE TABLE "DNBS11_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS12_FILING
--------------------------------------------------------

  CREATE TABLE "DNBS12_FILING" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS12_PART1_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS12_PART1_LAY1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "AMOUNT_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS12_PART1_LAY2
--------------------------------------------------------

  CREATE TABLE "DNBS12_PART1_LAY2" ("SR_NO" NUMBER, "INSTITUTION" VARCHAR2(200), "AMOUNT_X020" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS12_PART2_1
--------------------------------------------------------

  CREATE TABLE "DNBS12_PART2_1" ("SR_NO" VARCHAR2(50), "ASSERT_TYPE" VARCHAR2(200), "AMOUNT_X050" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS12_PART2_LAY1
--------------------------------------------------------

  CREATE TABLE "DNBS12_PART2_LAY1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "BOOK_VAL_X010" NUMBER(10,2), "RISK_WGT_X020" NUMBER(20,4), "ADJUST_VAL_X030" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS12_PART2_LAY2
--------------------------------------------------------

  CREATE TABLE "DNBS12_PART2_LAY2" ("SR_NO" VARCHAR2(50), "ASSERT_TYPE" VARCHAR2(200), "AMOUNT_X040" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS12_PART3_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS12_PART3_LY1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(300), "BOOK_VAL_X010" NUMBER(10,2), "CONV_FCTOR_X020" NUMBER(20,4), "EQUI_VAL_X030" NUMBER(10,2), "RISK_WGT_X040" NUMBER(20,4), "ADJUST_VAL_X050" NUMBER(10,2), "REMARKS_X060" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS12_PART3_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS12_PART3_LY2" ("SR_NO" NUMBER, "INTEREST_RT" VARCHAR2(300), "NO_TRANS_X070" NUMBER(10,2), "BOOK_VAL_X080" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS12_PART4
--------------------------------------------------------

  CREATE TABLE "DNBS12_PART4" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(300), "VAL_X010" NUMBER(20,4), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS12_PART5_1
--------------------------------------------------------

  CREATE TABLE "DNBS12_PART5_1" ("SR_NO" VARCHAR2(100), "PAN_X070" VARCHAR2(10), "NAME_SUBSID_X080" VARCHAR2(100), "NTR_CMP_X090" VARCHAR2(100), "OUT_AMNT_X0100" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS12_PART5_2
--------------------------------------------------------

  CREATE TABLE "DNBS12_PART5_2" ("SR_NO" VARCHAR2(100), "PAN_X0110" VARCHAR2(10), "NAME_OTR_CMP_X0120" VARCHAR2(100), "TYPE_X0130" VARCHAR2(100), "OUT_AMNT_X0140" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS12_PART5_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS12_PART5_LY1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(300), "VAL_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS12_PART5_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS12_PART5_LY2" ("SR_NO" VARCHAR2(100), "PAN_X020" VARCHAR2(10), "NAME_SUBSID_X030" VARCHAR2(100), "NTR_CMP_X040" VARCHAR2(100), "TYP_X050" VARCHAR2(100), "OUT_AMNT_X060" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS12_PART6
--------------------------------------------------------

  CREATE TABLE "DNBS12_PART6" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "AMN_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS12_PART7
--------------------------------------------------------

  CREATE TABLE "DNBS12_PART7" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "NO_CASES_X010" NUMBER(10,2), "AMN_X020" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS12_SCOP_QUE
--------------------------------------------------------

  CREATE TABLE "DNBS12_SCOP_QUE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS12_SIGN
--------------------------------------------------------

  CREATE TABLE "DNBS12_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS13_FILING_INFO
--------------------------------------------------------

  CREATE TABLE "DNBS13_FILING_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS13_FILING_INFO2
--------------------------------------------------------

  CREATE TABLE "DNBS13_FILING_INFO2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS13_SIGN
--------------------------------------------------------

  CREATE TABLE "DNBS13_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS13_TBL1
--------------------------------------------------------

  CREATE TABLE "DNBS13_TBL1" ("SR_NO" NUMBER, "NAME_JV_WOS" VARCHAR2(200), "COUNTRY" VARCHAR2(100), "DT_INCORP_X010" VARCHAR2(100), "DT_OBJECTION_X020" VARCHAR2(100), "BUSINESS_UNDRTKN_X030" VARCHAR2(100), "AMNT_REMI_QUART_X040" NUMBER(10,2), "AGRGT_OVERSES_NBFC_X050" NUMBER(20,4), "WTHR_OVERSES_WOS_X060" VARCHAR2(100), "NAME_REGU_X070" VARCHAR2(100), "SUPRVSR_CNSRN_X080" VARCHAR2(100), "PENALTY_INPOS_X090" VARCHAR2(100), "NTR_SPRT_JV_WOS_X0100" VARCHAR2(100), "RTEN_OBTND_WOS_JV_X0110" VARCHAR2(100), "FIN_DETAIL_WOSJV_SIZE_X0120" NUMBER(10,2), "FIN_DETAIL_WOSJV_PRFT_X0130" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS13_TBL2
--------------------------------------------------------

  CREATE TABLE "DNBS13_TBL2" ("SR_NO" NUMBER, "NAME_JV_WOS" VARCHAR2(200), "NAME_PARTNR" VARCHAR2(100), "SHR_HOLDPER_X0150" NUMBER(20,4), "CUMU_INVSTMNT_X0160" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS14_ANNEX1
--------------------------------------------------------

  CREATE TABLE "DNBS14_ANNEX1" ("SR_NO" NUMBER, "NAME" VARCHAR2(200), "TYPE_CAPITAL" VARCHAR2(200), "PAN_X010" VARCHAR2(10), "NUM_SHR_HELD_X020" NUMBER(10,2), "FC_VAL_X030" NUMBER(10,2), "PER_SHRHOLD_X040" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS14_ANNEX2
--------------------------------------------------------

  CREATE TABLE "DNBS14_ANNEX2" ("SR_NO" NUMBER, "NAME" VARCHAR2(200), "DT_APOINT_DIR" VARCHAR2(200), "DIN_X010" NUMBER, "PAN_X020" VARCHAR2(200), "CONTC_NUM_X030" NUMBER, "EMAIL_ID_X040" VARCHAR2(100), "NM_OTHR_CMP_X050" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS14_ANNEX3
--------------------------------------------------------

  CREATE TABLE "DNBS14_ANNEX3" ("SR_NO" NUMBER, "BRANCH_NAME_X010" VARCHAR2(200), "BRANCH_ADD_X020" VARCHAR2(100), "CITY_X030" VARCHAR2(100), "STATE_X040" VARCHAR2(100), "DISTRICT_X050" VARCHAR2(100), "OPENING_DT_X060" VARCHAR2(100), "CLOSING_DT_X070" VARCHAR2(100), "NO_DEPOSIT_ACC_X080" NUMBER, "AMT_PUB_DIPO_X090" NUMBER(10,2), "NO_LOAN_ACC_X100" NUMBER, "AMT_LOAN_ADVOUT_X110" NUMBER(10,2), "REMARK_X120" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS14_ANNEX4
--------------------------------------------------------

  CREATE TABLE "DNBS14_ANNEX4" ("SR_NO" VARCHAR2(20), "NAME_LENDER_X010" VARCHAR2(200), "PAN_LENDER_X020" VARCHAR2(10), "OCCU_LANDER_X030" VARCHAR2(100), "DT_REG_LENDER_X040" VARCHAR2(100), "LENDER_RATING_X050" VARCHAR2(100), "NAME_BORROWER_X060" VARCHAR2(100), "PAN_BORROWER_X070" VARCHAR2(10), "AVR_PERLENDR_X080" NUMBER(20,4), "EXP_OUT_X090" NUMBER(10,2), "STS_REMARK_X0100" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS14_ANNEX5
--------------------------------------------------------

  CREATE TABLE "DNBS14_ANNEX5" ("SR_NO" VARCHAR2(20), "NAME_BORROWER_X010" VARCHAR2(200), "PAN_NUMBER_X020" VARCHAR2(10), "LOAN_PURPOSE_X030" VARCHAR2(100), "DT_REG_BOROWER_X040" VARCHAR2(100), "BORROWER_RATING_X050" VARCHAR2(100), "NAME_LENDER_X060" VARCHAR2(100), "PAN_LENDER_X070" VARCHAR2(10), "AVR_PER_BORWR_X080" NUMBER(20,4), "TTL_BORROWR_AMNT_X090" NUMBER(10,2), "RES_MAT_X0100" NUMBER, "STS_REMARK_X0110" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS14_ANNEX6
--------------------------------------------------------

  CREATE TABLE "DNBS14_ANNEX6" ("SR_NO" VARCHAR2(20), "ESCROW_ACC_NO" NUMBER, "NAME_ESCROW_ACC_X010" VARCHAR2(100), "ESCROW_MAIN_X020" VARCHAR2(100), "DBT_SUM_ESCROW_X030" NUMBER(10,2), "CRDT_SUM_ESCROW_X040" NUMBER(10,2), "BLNCE_ESCROW_X050" NUMBER(10,2), "EXTRM_CASES_BAL_X060" NUMBER, "STS_REMAEK_X070" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS14_ANNEX7
--------------------------------------------------------

  CREATE TABLE "DNBS14_ANNEX7" ("SR_NO" VARCHAR2(50), "ESCROW_ACC_NO" NUMBER, "NAME_ESCROW_ACC_X010" VARCHAR2(100), "ESCROW_MAIN_X020" VARCHAR2(100), "DBT_SUM_ESCROW_X030" NUMBER(10,2), "CRDT_SUM_ESCROW_X040" NUMBER(10,2), "BLNCE_ESCROW_X050" NUMBER(10,2), "EXTRM_CASES_BAL_X060" NUMBER, "STS_REMAEK_X070" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS14_FILING
--------------------------------------------------------

  CREATE TABLE "DNBS14_FILING" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS14_PART1
--------------------------------------------------------

  CREATE TABLE "DNBS14_PART1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "AMOUNT_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS14_PART2
--------------------------------------------------------

  CREATE TABLE "DNBS14_PART2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "AMOUNT_X010" NUMBER(20,4), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS14_PART3
--------------------------------------------------------

  CREATE TABLE "DNBS14_PART3" ("SR_NO" NUMBER, "INCOME_ITEMS" VARCHAR2(200), "AMOUNT_X010" NUMBER(20,4), "REMARK_X20" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS14_PART4
--------------------------------------------------------

  CREATE TABLE "DNBS14_PART4" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "AMOUNT_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS14_PART5_LY1
--------------------------------------------------------

  CREATE TABLE "DNBS14_PART5_LY1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "NAME_X010" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS14_PART5_LY2
--------------------------------------------------------

  CREATE TABLE "DNBS14_PART5_LY2" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(200), "END_PREVIOUS_QTR_X020" NUMBER(10,2), "NO_NEW_ACC_QTR_X030" NUMBER(10,2), "NO_CLOED_ACC_QTR_X040" NUMBER(10,2), "NO_ACC_ED_QTR_X050" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS14_PART5_LY3
--------------------------------------------------------

  CREATE TABLE "DNBS14_PART5_LY3" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(200), "END_PREVIOUS_QTR_X060" NUMBER(10,2), "AMT_DEPOSITE_QTR_X070" NUMBER(10,2), "AMT_WITHDROW_QTR_X080" NUMBER(10,2), "TOT_AMT_ED_QTR_X090" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS14_PART5_LY4
--------------------------------------------------------

  CREATE TABLE "DNBS14_PART5_LY4" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(200), "END_PREVIOUS_QTR_X100" NUMBER(10,2), "RECI_NEWCOMPLAINT_X110" NUMBER(10,2), "NO_COMPLAINT_DESPOS_X120" NUMBER(10,2), "TOT_NOCPMPLAINT_OUT_X130" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS14_PART5_LY5
--------------------------------------------------------

  CREATE TABLE "DNBS14_PART5_LY5" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE_X140" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS14_PART6
--------------------------------------------------------

  CREATE TABLE "DNBS14_PART6" ("SR_NO" NUMBER, "ASSET_CLAS_STS" VARCHAR2(200), "AMT_OUT_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS14_PART7
--------------------------------------------------------

  CREATE TABLE "DNBS14_PART7" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(200), "AMOUNT_X010" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS14_PART8
--------------------------------------------------------

  CREATE TABLE "DNBS14_PART8" ("SR_NO" NUMBER, "DELINQUENCY_PERIOD" VARCHAR2(200), "AMT_BEGING_QTR_X010" NUMBER(10,2), "AMT_ADDITION_QTR_X020" NUMBER(10,2), "AMT_RECOVERY_QTR_X030" NUMBER(10,2), "AMT_END_QTR_X040" NUMBER(10,2), "NO_ACC_END_QTR_X050" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS14_SIGN
--------------------------------------------------------

  CREATE TABLE "DNBS14_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS17_ASSSIZE_GREATER_500CR_L1
--------------------------------------------------------

  CREATE TABLE "DNBS17_ASSSIZE_GREATER_500CR_L1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "WHE_IMPLTEMENTED_X010" VARCHAR2(250), "NOT_REAS_DELAY_X020" VARCHAR2(100), "EXPE_TIME_X030" VARCHAR2(100), "MIGRATION_CONTROL_X040" VARCHAR2(100), "REMARKS_X050" VARCHAR2(100), "REASON1_X060" VARCHAR2(100), "REASON2_X070" VARCHAR2(100), "REASON3_X080" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS17_ASSSIZE_GREATER_500CR_L2
--------------------------------------------------------

  CREATE TABLE "DNBS17_ASSSIZE_GREATER_500CR_L2" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(200), "DEATIALS_X090" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS17_ASSSIZE_GREATER_500CR_L3
--------------------------------------------------------

  CREATE TABLE "DNBS17_ASSSIZE_GREATER_500CR_L3" ("SR_NO" NUMBER, "NAME_ACT_X0100" VARCHAR2(200), "NAME_VENDOR_X0110" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS17_ASS_SIZE_LESS_500CR
--------------------------------------------------------

  CREATE TABLE "DNBS17_ASS_SIZE_LESS_500CR" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "WHE_IMPLTEMENTED_X010" VARCHAR2(250), "NOT_REAS_DELAY_X020" VARCHAR2(100), "EXPE_TIME_X030" VARCHAR2(100), "MIGRATION_CONTROL_X040" VARCHAR2(100), "REMARKS_X050" VARCHAR2(100), "REASON1_X060" VARCHAR2(100), "REASON2_X070" VARCHAR2(100), "REASON3_X080" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS17_ASS_SIZE_LESS_500CR_L2
--------------------------------------------------------

  CREATE TABLE "DNBS17_ASS_SIZE_LESS_500CR_L2" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(200), "X090" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS17_ASS_SIZE_LESS_500CR_L3
--------------------------------------------------------

  CREATE TABLE "DNBS17_ASS_SIZE_LESS_500CR_L3" ("SR_NO" NUMBER, "NAME_ACT_X0100" VARCHAR2(200), "NAME_VENDOR_X0110" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS17_FILING_L1
--------------------------------------------------------

  CREATE TABLE "DNBS17_FILING_L1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS17_FILING_L2
--------------------------------------------------------

  CREATE TABLE "DNBS17_FILING_L2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS17_SCOP_QUE
--------------------------------------------------------

  CREATE TABLE "DNBS17_SCOP_QUE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS17_SIGN
--------------------------------------------------------

  CREATE TABLE "DNBS17_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS4A_FILING
--------------------------------------------------------

  CREATE TABLE "DNBS4A_FILING" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS4A_SCOP_QUE
--------------------------------------------------------

  CREATE TABLE "DNBS4A_SCOP_QUE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS4A_SIGN
--------------------------------------------------------

  CREATE TABLE "DNBS4A_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS4A_TBL1
--------------------------------------------------------

  CREATE TABLE "DNBS4A_TBL1" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(200), "DAY0_7_X010" NUMBER(20,4), "DAY8_14_X020" NUMBER(20,4), "DAY15_30_31_X030" NUMBER(20,4), "MONTH1_3_X040" NUMBER(20,4), "MONTH3_6_X050" NUMBER(20,4), "TOTAL_X060" NUMBER(20,4), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS4A_TBL2
--------------------------------------------------------

  CREATE TABLE "DNBS4A_TBL2" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(200), "DAY0_7_X070" NUMBER(20,4), "DAY8_14_X080" NUMBER(20,4), "DAY15_30_31_X090" NUMBER(20,4), "MONTH1_3_X100" NUMBER(20,4), "MONTH3_6_X110" NUMBER(20,4), "TOTAL_X120" NUMBER(20,4), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS4B_AUTH_SIGN
--------------------------------------------------------

  CREATE TABLE "DNBS4B_AUTH_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(300), "VALUE" VARCHAR2(300), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS4B_BIRS_1
--------------------------------------------------------

  CREATE TABLE "DNBS4B_BIRS_1" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(200), "DAY0_7_X010" NUMBER(20,4), "DAY8_14_X020" NUMBER(20,4), "DAY15_30_31_X030" NUMBER(20,4), "MONTH1_2_X040" NUMBER(20,4), "MONTH2_3_X050" NUMBER(20,4), "MONTH3_6_X060" NUMBER(20,4), "MONTH6_1Y_X070" NUMBER(20,4), "YEAR1_3Y_X080" NUMBER(20,4), "YEAR3_5Y_X090" NUMBER(20,4), "YEAR5_X100" NUMBER(20,4), "NONSENSITITIVE_X110" NUMBER(20,4), "TOTAL_X120" NUMBER(20,4), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS4B_BIRS_2
--------------------------------------------------------

  CREATE TABLE "DNBS4B_BIRS_2" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(200), "DAY0_7_X130" NUMBER(20,4), "DAY8_14_X140" NUMBER(20,4), "DAY15_30_31_X150" NUMBER(20,4), "MONTH1_2_X160" NUMBER(20,4), "MONTH2_3_X170" NUMBER(20,4), "MONTH3_6_X180" NUMBER(20,4), "MONTH6_1Y_X190" NUMBER(20,4), "YEAR1_3Y_X200" NUMBER(20,4), "YEAR3_5Y_X210" NUMBER(20,4), "YEAR5_X220" NUMBER(20,4), "NONSENSITITIVE_X230" NUMBER(20,4), "TOTAL_X240" NUMBER(20,4), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS4B_BLCR
--------------------------------------------------------

  CREATE TABLE "DNBS4B_BLCR" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(2000), "TOTAL_UNWEIGHTED_X010" NUMBER(20,4), "FACTOR_X020" NUMBER(20,4), "TOTAL_WEIGHTED_X030" NUMBER(20,4), "REMARKS_X080" VARCHAR2(200), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS4B_BLCR_1
--------------------------------------------------------

  CREATE TABLE "DNBS4B_BLCR_1" ("SR_NO" NUMBER, "NAME_COUNTRY" VARCHAR2(2000), "UNWEIGHTED_AMOUNT_X050" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS4B_BLCR_2
--------------------------------------------------------

  CREATE TABLE "DNBS4B_BLCR_2" ("SR_NO" NUMBER, "NAME_ISSUER" VARCHAR2(2000), "UNWEIGHTED_AMOUNT_X060" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS4B_BLCR_3
--------------------------------------------------------

  CREATE TABLE "DNBS4B_BLCR_3" ("SR_NO" NUMBER, "NAME_ISSUER_COUNTRY" VARCHAR2(2000), "UNWEIGHTED_AMOUNT_X070" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS4B_COLL_DISB
--------------------------------------------------------

  CREATE TABLE "DNBS4B_COLL_DISB" ("SR_NO" NUMBER, "NBFC_LOAN_PORTFOLIO" VARCHAR2(200), "ACTUAL_DISBURSAL_X010" NUMBER(20,4), "PROJECTED_DISBURSAL_REPORTING_X020" NUMBER(20,4), "PROJECTED_DISBURSAL_DURING_X030" NUMBER(20,4), "ACTUAL_COLLECTIONS_X040" NUMBER(20,4), "CONTRACTUAL_COLLECTIONS_DURING_REPORTING_X050" NUMBER(20,4), "CONTRACTUAL_COLLECTIONS_DURING_NEXT_X060" NUMBER(20,4), "COLLECTIONS_EFFICIENCY_X070" NUMBER(20,4), "REMARKS_X080" VARCHAR2(200), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS4B_FILING_INFO
--------------------------------------------------------

  CREATE TABLE "DNBS4B_FILING_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(300), "VALUE" VARCHAR2(300), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS4B_FILING_INFO2
--------------------------------------------------------

  CREATE TABLE "DNBS4B_FILING_INFO2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(300), "VALUE" VARCHAR2(300), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table DNBS4B_STRU_LIQ
--------------------------------------------------------

  CREATE TABLE "DNBS4B_STRU_LIQ" ("SR_NO" NUMBER, "PARTICULARS" NVARCHAR2(600), "DAY0_7_X010" NUMBER(20,4), "DAY8_14_X020" NUMBER(20,4), "DAY15_30_31_X030" NUMBER(20,4), "MONTH1_2_X040" NUMBER(20,4), "MONTH2_3_X050" NUMBER(20,4), "MONTH3_6_X060" NUMBER(20,4), "MONTH6_1Y_X070" NUMBER(20,4), "YEAR1_3Y_X080" NUMBER(20,4), "YEAR3_5Y_X090" NUMBER(20,4), "YEAR5_X0100" NUMBER(20,4), "TOTAL_X0110" NUMBER(20,4), "REMARKS_X0120" VARCHAR2(200), "DAY0_7_X0130" NUMBER(20,4), "DAY8_14_X0140" NUMBER(20,4), "DAY15_30_31_X0150" NUMBER(20,4), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table EMAILS
--------------------------------------------------------

  CREATE TABLE "EMAILS" ("EMAIL_ID" NUMBER, "EMAIL" VARCHAR2(150));

--------------------------------------------------------
--  DDL for Table ENTITY_CONFIG
--------------------------------------------------------

  CREATE TABLE "ENTITY_CONFIG" ("ENTITY_NAME" VARCHAR2(1020), "ARGUMENTS" VARCHAR2(1020), "RE_VALIDATION_ARGS" VARCHAR2(1020));

--------------------------------------------------------
--  DDL for Table ERR$_STUDENT_DEMO_DEST
--------------------------------------------------------

  CREATE TABLE "ERR$_STUDENT_DEMO_DEST" ("ORA_ERR_NUMBER$" NUMBER, "ORA_ERR_MESG$" VARCHAR2(2000), "ORA_ERR_ROWID$" UROWID, "ORA_ERR_OPTYP$" VARCHAR2(2), "ORA_ERR_TAG$" VARCHAR2(2000), "SR_NO" VARCHAR2(4000), "FULL_NAME" VARCHAR2(4000), "GENDER" VARCHAR2(4000), "AGE" VARCHAR2(4000), "CITY" VARCHAR2(4000), "DOB" VARCHAR2(4000));

--------------------------------------------------------
--  DDL for Table EXTERNAL_RAT_MASTER_CIMS
--------------------------------------------------------

  CREATE TABLE "EXTERNAL_RAT_MASTER_CIMS" ("RATING" VARCHAR2(500));

--------------------------------------------------------
--  DDL for Table FIMD_RAL_ANNEX1_2
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_ANNEX1_2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DEBIT_ENTRI_NO" NUMBER(10,2), "DEBIT_ENTRI_AMNT" NUMBER(10,2), "CREDIT_ENTRI_NO" NUMBER(10,2), "CREDIT_ENTRI_AMNT" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_ANNEX3
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_ANNEX3" ("SR_NO" NUMBER, "NAME_DUE_FROM" VARCHAR2(200), "AMOUNT_DUE" NUMBER(10,2), "PROVISION_MADE" NUMBER(10,2), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_ANNEX_3B
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_ANNEX_3B" ("SR_NO" NUMBER, "NAME_DUE_FROM" VARCHAR2(200), "AMOUNT_DUE" NUMBER(10,2), "PROVISION_MADE" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_ANNEX_3C
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_ANNEX_3C" ("SR_NO" NUMBER, "NAME_DUE_FROM" VARCHAR2(200), "AMOUNT_DUE" NUMBER(10,2), "PROVISION_MADE" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_ANNEX_ACC_BAL
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_ANNEX_ACC_BAL" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "AMOUNT" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_GEN_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC1_PARTA
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC1_PARTA" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOMESTIC_OPS_TOT" NUMBER(10,2), "DOMESTIC_OPS_OFF_HELD_FOREX" NUMBER(10,2), "OVERSEAS_OPS_TOT" NUMBER(10,2), "OVERSEAS_OPS_OFF_HELD_FOREX" NUMBER(10,2), "GLOBAL_OPS_TOT" NUMBER(10,2), "GLOBAL_OPS_OFF_HELD_FOREX" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC1_PARTA_OTH
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC1_PARTA_OTH" ("SR_NO" NUMBER, "ASSETS" VARCHAR2(200), "DOMESTIC_OPS_TOT" NUMBER(10,2), "DOMESTIC_OPS_OFF_HELD_FOREX" NUMBER(10,2), "OVERSEAS_OPS_TOT" NUMBER(10,2), "OVERSEAS_OPS_OFF_HELD_FOREX" NUMBER(10,2), "GLOBAL_OPS_TOT" NUMBER(10,2), "GLOBAL_OPS_OFF_HELD_FOREX" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC1_PARTA_OTH1
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC1_PARTA_OTH1" ("SR_NO" NUMBER, "ASSETS" VARCHAR2(200), "DOMESTIC_OPS_TOT" NUMBER(10,2), "DOMESTIC_OPS_OFF_HELD_FOREX" NUMBER(10,2), "OVERSEAS_OPS_TOT" NUMBER(10,2), "OVERSEAS_OPS_OFF_HELD_FOREX" NUMBER(10,2), "GLOBAL_OPS_TOT" NUMBER(10,2), "GLOBAL_OPS_OFF_HELD_FOREX" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC1_PARTA_OTH2
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC1_PARTA_OTH2" ("SR_NO" NUMBER, "ASSETS" VARCHAR2(200), "DOMESTIC_OPS_TOT" NUMBER(10,2), "DOMESTIC_OPS_OFF_HELD_FOREX" NUMBER(10,2), "OVERSEAS_OPS_TOT" NUMBER(10,2), "OVERSEAS_OPS_OFF_HELD_FOREX" NUMBER(10,2), "GLOBAL_OPS_TOT" NUMBER(10,2), "GLOBAL_OPS_OFF_HELD_FOREX" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC1_PARTA_OTH3
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC1_PARTA_OTH3" ("SR_NO" NUMBER, "ASSETS" VARCHAR2(200), "DOMESTIC_OPS_TOT" NUMBER(10,2), "DOMESTIC_OPS_OFF_HELD_FOREX" NUMBER(10,2), "OVERSEAS_OPS_TOT" NUMBER(10,2), "OVERSEAS_OPS_OFF_HELD_FOREX" NUMBER(10,2), "GLOBAL_OPS_TOT" NUMBER(10,2), "GLOBAL_OPS_OFF_HELD_FOREX" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC1_PARTA_OTH4
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC1_PARTA_OTH4" ("SR_NO" NUMBER, "ASSETS" VARCHAR2(200), "DOMESTIC_OPS_TOT" NUMBER(10,2), "DOMESTIC_OPS_OFF_HELD_FOREX" NUMBER(10,2), "OVERSEAS_OPS_TOT" NUMBER(10,2), "OVERSEAS_OPS_OFF_HELD_FOREX" NUMBER(10,2), "GLOBAL_OPS_TOT" NUMBER(10,2), "GLOBAL_OPS_OFF_HELD_FOREX" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC1_PARTA_OTH5
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC1_PARTA_OTH5" ("SR_NO" NUMBER, "ASSETS" VARCHAR2(200), "DOMESTIC_OPS_TOT" NUMBER(10,2), "DOMESTIC_OPS_OFF_HELD_FOREX" NUMBER(10,2), "OVERSEAS_OPS_TOT" NUMBER(10,2), "OVERSEAS_OPS_OFF_HELD_FOREX" NUMBER(10,2), "GLOBAL_OPS_TOT" NUMBER(10,2), "GLOBAL_OPS_OFF_HELD_FOREX" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC1_PARTB
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC1_PARTB" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOMESTIC_OPS_TOT" NUMBER(10,2), "DOMESTIC_OPS_OFF_HELD_FOREX" NUMBER(10,2), "OVERSEAS_OPS_TOT" NUMBER(10,2), "OVERSEAS_OPS_OFF_HELD_FOREX" NUMBER(10,2), "GLOBAL_OPS_TOT" NUMBER(10,2), "GLOBAL_OPS_OFF_HELD_FOREX" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC1_PARTB_OTH
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC1_PARTB_OTH" ("SR_NO" NUMBER, "ASSETS" VARCHAR2(200), "DOMESTIC_OPS_TOT" NUMBER(10,2), "DOMESTIC_OPS_OFF_HELD_FOREX" NUMBER(10,2), "OVERSEAS_OPS_TOT" NUMBER(10,2), "OVERSEAS_OPS_OFF_HELD_FOREX" NUMBER(10,2), "GLOBAL_OPS_TOT" NUMBER(10,2), "GLOBAL_OPS_OFF_HELD_FOREX" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC1_PARTC
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC1_PARTC" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOMESTIC_OPS_TOT" NUMBER(10,2), "DOMESTIC_OPS_OFF_HELD_FOREX" NUMBER(10,2), "OVERSEAS_OPS_TOT" NUMBER(10,2), "OVERSEAS_OPS_OFF_HELD_FOREX" NUMBER(10,2), "GLOBAL_OPS_TOT" NUMBER(10,2), "GLOBAL_OPS_OFF_HELD_FOREX" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC1_PARTC_OTH
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC1_PARTC_OTH" ("SR_NO" NUMBER, "ASSETS" VARCHAR2(200), "DOMESTIC_OPS_TOT" NUMBER(10,2), "DOMESTIC_OPS_OFF_HELD_FOREX" NUMBER(10,2), "OVERSEAS_OPS_TOT" NUMBER(10,2), "OVERSEAS_OPS_OFF_HELD_FOREX" NUMBER(10,2), "GLOBAL_OPS_TOT" NUMBER(10,2), "GLOBAL_OPS_OFF_HELD_FOREX" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC1_PARTD
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC1_PARTD" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOMESTIC_OPS_BOOK_VAL" NUMBER(10,2), "DOMESTIC_OPS_CREDIT_EQUIV" NUMBER(10,2), "OVERSEAS_OPS_BOOK_VAL" NUMBER(10,2), "OVERSEAS_OPS_CREDIT_EQUIV" NUMBER(10,2), "GLOBAL_OPS_BOOK_VAL" NUMBER(10,2), "GLOBAL_OPS_CREDIT_EQUIV" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC2_PARTA
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC2_PARTA" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOMESTIC_OPS_BOOK_VAL" NUMBER(10,2), "DOMESTIC_OPS_CREDIT_EQUIV" NUMBER(10,2), "OVERSEAS_OPS_BOOK_VAL" NUMBER(10,2), "OVERSEAS_OPS_CREDIT_EQUIV" NUMBER(10,2), "GLOBAL_OPS_BOOK_VAL" NUMBER(10,2), "GLOBAL_OPS_CREDIT_EQUIV" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC2_PARTB_C
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC2_PARTB_C" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "PRINCIPAL_AMT_TURN_MNTH" NUMBER(10,2), "PRINCIPAL_AMT_OUTSTANDING" NUMBER(10,2), "TRADING_BK_TURN_MNTH" NUMBER(10,2), "TRADING_BK_OUTSTANDING" NUMBER(10,2), "BANKING_BK_TURN_MNTH" NUMBER(10,2), "BANKING_BK_OUTSTANDING" NUMBER(10,2), "CREDIT_EQUITY_PRINC_AMO" NUMBER(10,2), "CREDIT_EQUITY_TRANDING_BK" NUMBER(10,2), "CREDIT_EQUITY_BANKING_BK" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC2_PARTB_C_OTH1
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC2_PARTB_C_OTH1" ("SR_NO" NUMBER, "CONTRACT_DERIV" VARCHAR2(200), "PRINCIPAL_AMT_TURN_MNTH" NUMBER(10,2), "PRINCIPAL_AMT_OUTSTANDING" NUMBER(10,2), "TRADING_BK_TURN_MNTH" NUMBER(10,2), "TRADING_BK_OUTSTANDING" NUMBER(10,2), "BANKING_BK_TURN_MNTH" NUMBER(10,2), "BANKING_BK_OUTSTANDING" NUMBER(10,2), "CREDIT_EQUITY_PRINC_AMO" NUMBER(10,2), "CREDIT_EQUITY_TRANDING_BK" NUMBER(10,2), "CREDIT_EQUITY_BANKING_BK" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC2_PARTB_C_OTH2
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC2_PARTB_C_OTH2" ("SR_NO" NUMBER, "CONTRACT_DERIV" VARCHAR2(200), "PRINCIPAL_AMT_TURN_MNTH" NUMBER(10,2), "PRINCIPAL_AMT_OUTSTANDING" NUMBER(10,2), "TRADING_BK_TURN_MNTH" NUMBER(10,2), "TRADING_BK_OUTSTANDING" NUMBER(10,2), "BANKING_BK_TURN_MNTH" NUMBER(10,2), "BANKING_BK_OUTSTANDING" NUMBER(10,2), "CREDIT_EQUITY_PRINC_AMO" NUMBER(10,2), "CREDIT_EQUITY_TRANDING_BK" NUMBER(10,2), "CREDIT_EQUITY_BANKING_BK" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC2_PART_D1
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC2_PART_D1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "NAT_PRINC_TOTAL" NUMBER(10,2), "NAT_PRINCI_OUT_TOTAL" NUMBER(10,2), "CREDITEQUIVALENT_CURRENT_CREDITEXP" NUMBER(10,2), "CREDITEQUIVALENT_POTENTIAL_FUTUREEXP" NUMBER(10,2), "NEGATIVE_MTM_VAL" NUMBER(10,2), "PVBP_SANCTIONED" NUMBER(10,2), "PVBP_ACTUAL" NUMBER(10,2), "VAR_SANCTIONED" NUMBER(10,2), "VAR_ACTUAL" NUMBER(10,2), "REMARK" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC2_PART_D1_OTH
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC2_PART_D1_OTH" ("SR_NO" NUMBER, "DERIVATIVE" VARCHAR2(200), "NAT_PRINC_TOTAL" NUMBER(10,2), "NAT_PRINCI_OUT_TOTAL" NUMBER(10,2), "CREDITEQUIVALENT_CURRENT_CREDITEXP" NUMBER(10,2), "CREDITEQUIVALENT_POTENTIAL_FUTUREEXP" NUMBER(10,2), "NEGATIVE_MTM_VAL" NUMBER(10,2), "PVBP_SANCTIONED" NUMBER(10,2), "PVBP_ACTUAL" NUMBER(10,2), "VAR_SANCTIONED" NUMBER(10,2), "VAR_ACTUAL" NUMBER(10,2), "REMARK" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC2_PART_D2
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC2_PART_D2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "NAT_PRINC_TOTAL" NUMBER(10,2), "NAT_PRINCI_OUT_TOTAL" NUMBER(10,2), "CREDITEQUIVALENT_CURRENT_CREDITEXP" NUMBER(10,2), "CREDITEQUIVALENT_POTENTIAL_FUTUREEXP" NUMBER(10,2), "NEGATIVE_MTM_VAL" NUMBER(10,2), "PVBP_SANCTIONED" NUMBER(10,2), "PVBP_ACTUAL" NUMBER(10,2), "VAR_SANCTIONED" NUMBER(10,2), "VAR_ACTUAL" NUMBER(10,2), "REMARK" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC2_PART_D2_OTH
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC2_PART_D2_OTH" ("SR_NO" NUMBER, "DERIVATIVE" VARCHAR2(200), "NAT_PRINC_TOTAL" NUMBER(10,2), "NAT_PRINCI_OUT_TOTAL" NUMBER(10,2), "CREDITEQUIVALENT_CURRENT_CREDITEXP" NUMBER(10,2), "CREDITEQUIVALENT_POTENTIAL_FUTUREEXP" NUMBER(10,2), "NEGATIVE_MTM_VAL" NUMBER(10,2), "PVBP_SANCTIONED" NUMBER(10,2), "PVBP_ACTUAL" NUMBER(10,2), "VAR_SANCTIONED" NUMBER(10,2), "VAR_ACTUAL" NUMBER(10,2), "REMARK" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC2_PART_E1
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC2_PART_E1" ("SR_NO" NUMBER, "DERIVATIVE" VARCHAR2(200), "TRAD_BANK_PAY" NUMBER(10,2), "TRAD_BANK_RECEIV" NUMBER(10,2), "HEDGING_BANK_PAY" NUMBER(10,2), "HEDGING_BANK_RECEIVE" NUMBER(10,2), "TOTAL_NAT_PRINC" NUMBER(10,2), "GROSS_REC_TB" NUMBER(10,2), "GROSS_REC_BB" NUMBER(10,2), "GROSS_REC_TOTAL" NUMBER(10,2), "GROSS_PAID_TB" NUMBER(10,2), "GROSS_PAID_BB" NUMBER(10,2), "GROSS_PAID_TOTAL" NUMBER(10,2), "HIGHER" NUMBER(10,2), "NET_PVBP01" NUMBER(10,2), "REMARK" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC2_PART_E2
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC2_PART_E2" ("SR_NO" NUMBER, "DERIVATIVE" VARCHAR2(200), "TRAD_BANK_PAY" NUMBER(10,2), "TRAD_BANK_RECEIV" NUMBER(10,2), "HEDGING_BANK_PAY" NUMBER(10,2), "HEDGING_BANK_RECEIVE" NUMBER(10,2), "TOTAL_NAT_PRINC" NUMBER(10,2), "GROSS_REC_TB" NUMBER(10,2), "GROSS_REC_BB" NUMBER(10,2), "GROSS_REC_TOTAL" NUMBER(10,2), "GROSS_PAID_TB" NUMBER(10,2), "GROSS_PAID_BB" NUMBER(10,2), "GROSS_PAID_TOTAL" NUMBER(10,2), "HIGHER" NUMBER(10,2), "NET_PVBP01" NUMBER(10,2), "REMARK" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC2_PART_F1
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC2_PART_F1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "APRIL_DT_PROTECTIONBUYER" NUMBER(10,2), "APRIL_DT_PROTECTIONSELLER" NUMBER(10,2), "END_MONTH_PROTECTIONBUYER" NUMBER(10,2), "END_MONTH_PROTECTIONSELLER" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC2_PART_F2
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC2_PART_F2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "APRIL_DT_PROTECTIONBUYER" NUMBER(10,2), "APRIL_DT_PROTECTIONSELLER" NUMBER(10,2), "END_MONTH_PROTECTIONBUYER" NUMBER(10,2), "END_MONTH_PROTECTIONSELLER" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC2_PART_G1G2
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC2_PART_G1G2" ("SR_NO" NUMBER, "NAME_BANK" VARCHAR2(100), "NATIONAL_AMNT" NUMBER(10,2), "CURR_CRED_EXP" NUMBER(10,2), "POT_FUTU_EXP" NUMBER(10,2), "NIENTY_DAY_PAST" NUMBER(10,2), "ACTUAL_CRED_LOSS" NUMBER(10,2), "RESTRUCTED_CONTR" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC2_PART_G1G2T2
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC2_PART_G1G2T2" ("SR_NO" NUMBER, "NAME_COUNTERPARTY" VARCHAR2(100), "NATIONAL_AMNT" NUMBER(10,2), "CURR_CRED_EXP" NUMBER(10,2), "POT_FUTU_EXP" NUMBER(10,2), "NIENTY_DAY_PAST" NUMBER(10,2), "ACTUAL_CRED_LOSS" NUMBER(10,2), "RESTRUCTED_CONTR" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC2_PART_G1G2T3
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC2_PART_G1G2T3" ("SR_NO" NUMBER, "NAME_COUNTERPARTY" VARCHAR2(100), "NATIONAL_AMNT" NUMBER(10,2), "CURR_CRED_EXP" NUMBER(10,2), "POT_FUTU_EXP" NUMBER(10,2), "NIENTY_DAY_PAST" NUMBER(10,2), "ACTUAL_CRED_LOSS" NUMBER(10,2), "RESTRUCTED_CONTR" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC2_PART_G1G2T4
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC2_PART_G1G2T4" ("SR_NO" NUMBER, "NAME_COUNTERPARTY" VARCHAR2(100), "NATIONAL_AMNT" NUMBER(10,2), "CURR_CRED_EXP" NUMBER(10,2), "POT_FUTU_EXP" NUMBER(10,2), "NIENTY_DAY_PAST" NUMBER(10,2), "ACTUAL_CRED_LOSS" NUMBER(10,2), "RESTRUCTED_CONTR" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC3_PARTA
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC3_PARTA" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "MERCHAT_SPOT_CASH_READY" NUMBER(10,2), "MERCHAT_FRWD" NUMBER(10,2), "MERCHAT_CANC_FRWD" NUMBER(10,2), "INTERBANK_SPOT" NUMBER(10,2), "INTERBANK_SWAP" NUMBER(10,2), "INTERBANK_FRWD" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC3_PARTB
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC3_PARTB" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "HTM" NUMBER(10,2), "HFT" NUMBER(10,2), "AFS" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SEC3_PARTC
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SEC3_PARTC" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "HTM_BOUGHT" NUMBER(10,2), "HTM_SOLD" NUMBER(10,2), "HTM_TOTAL" NUMBER(10,2), "HFT_BOUGHT" NUMBER(10,2), "HFT_SOLD" NUMBER(10,2), "HFT_TOTAL" NUMBER(10,2), "AFS_BOUGHT" NUMBER(10,2), "AFS_SOLD" NUMBER(10,2), "AFS_TOTAL" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAL_SIGNATORY
--------------------------------------------------------

  CREATE TABLE "FIMD_RAL_SIGNATORY" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "AUTH_REP_OFFICI" VARCHAR2(100), "COUNTERSIGNED_BY" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_AQ_PROFILE_QTR2
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_AQ_PROFILE_QTR2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "STANDARD" NUMBER(10,2), "SUB_STANDARD" NUMBER(10,2), "DOUBTFUL" NUMBER(10,2), "LOSS" NUMBER(10,2), "TOTAL" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_CHANGE_AQ_MOV
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_CHANGE_AQ_MOV" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "STANDARD" NUMBER(10,2), "SUB_STANDARD" NUMBER(10,2), "DOUBTFUL" NUMBER(10,2), "LOSS" NUMBER(10,2), "TOTAL" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_CHANGE_AQ_NPA
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_CHANGE_AQ_NPA" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "SUB_STANDARD" NUMBER(10,2), "DOUBTFUL" NUMBER(10,2), "LOSS" NUMBER(10,2), "TOTAL" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_CHANGE_AQ_PARTC_MOVE
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_CHANGE_AQ_PARTC_MOVE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_CHANGE_AQ_PARTD
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_CHANGE_AQ_PARTD" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "NO_OF_CASES" NUMBER, "VALUE" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_CLASS_RISK_ASSET_PARTA
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_CLASS_RISK_ASSET_PARTA" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "GROSS_AMT" NUMBER(20,2), "PERCENT_TOTAL_GROSS" NUMBER(20,4), "BAL_INTREST_SUSPENSE" NUMBER(20,2), "ECGC_CLAIM_ADJT" NUMBER(20,2), "PART_PAY" NUMBER(20,2), "PROVISION_HELD" NUMBER(20,2), "PROVISION_PERCENT_GROSS" NUMBER(20,4), "NET_ADV" NUMBER(20,2), "PERCENT_NET_ADV" NUMBER(20,4), "AMT_WRITE_OFF" NUMBER(20,2), "INT_ON_NPA" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_CLASS_RISK_ASSET_PARTA_DATE
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_CLASS_RISK_ASSET_PARTA_DATE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_CLASS_RISK_ASSET_PARTA_MEMO
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_CLASS_RISK_ASSET_PARTA_MEMO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_CLASS_RISK_ASSET_PARTB
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_CLASS_RISK_ASSET_PARTB" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "STANDARD" NUMBER(10,2), "SUB_STANDARD" NUMBER(10,2), "DOUBTFUL" NUMBER(10,2), "LOSS" NUMBER(10,2), "TOTAL" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_CLASS_RISK_ASSET_PARTC_MOV
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_CLASS_RISK_ASSET_PARTC_MOV" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_COUNT_RISK
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_COUNT_RISK" ("SR_NO" NUMBER, "CONTRY_BORRO" VARCHAR2(200), "CONTRY_RISK" VARCHAR2(200), "SECTOR" VARCHAR2(200), "STANDRAD" NUMBER(20,2), "SUBSTD" NUMBER(20,2), "DOUBTFUL" NUMBER(20,2), "LOSS" NUMBER(20,2), "TOTAL" NUMBER(20,2), "OFF_WHICH_SHORT" NUMBER(20,2), "NFE_TOTAL" NUMBER(20,2), "NFE_OFF_WHICH_SHRT" NUMBER(20,2), "GNFE" NUMBER(20,2), "PROV_HELD" NUMBER(20,2), "PROV_PER" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_COUNT_RISK_TOT
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_COUNT_RISK_TOT" ("SR_NO" NUMBER, "STANDRAD" NUMBER(20,2), "SUBSTD" NUMBER(20,2), "DOUBTFUL" NUMBER(20,2), "LOSS" NUMBER(20,2), "TOTAL" NUMBER(20,2), "OFF_WHICH_SHORT" NUMBER(20,2), "NFE_TOTAL" NUMBER(20,2), "NFE_OFF_WHICH_SHRT" NUMBER(20,2), "GNFE" NUMBER(20,2), "PROV_HELD" NUMBER(20,2), "PROV_PER" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE, "DESCRIPTION" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_EXP_CR
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_EXP_CR" ("SR_NO" NUMBER, "PRE_RUPEE_CREDIT" NUMBER(10,2), "PRE_PCFC" NUMBER(10,2), "PRE_TOTAL" NUMBER(10,2), "POST_RUPEE_CREDIT" NUMBER(10,2), "POST_EBR" NUMBER(10,2), "POST_DEF_PAY" NUMBER(10,2), "POST_GOV_PAY" NUMBER(10,2), "POST_TOT" NUMBER(10,2), "TOTAL" NUMBER(10,2), "PRE_RUPEE_CREDIT_EOQ" NUMBER(10,2), "PRE_PCFC_EOQ" NUMBER(10,2), "PRE_TOTAL_EOQ" NUMBER(10,2), "POST_RUPEE_CREDIT_EOQ" NUMBER(10,2), "POST_EBR_EOQ" NUMBER(10,2), "POST_DEF_PAY_EOQ" NUMBER(10,2), "POST_GOV_PAY_EOQ" NUMBER(10,2), "POST_TOT_EOQ" NUMBER(10,2), "TOTAL_EOQ" NUMBER(10,2), "GOLD_CARDS" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_EXP_CR_2
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_EXP_CR_2" ("SR_NO" NUMBER, "PRE_RUPEE_CREDIT" NUMBER(10,2), "PRE_PCFC" NUMBER(10,2), "PRE_TOTAL" NUMBER(10,2), "POST_RUPEE_CREDIT" NUMBER(10,2), "POST_EBR" NUMBER(10,2), "POST_DEF_PAY" NUMBER(10,2), "POST_GOV_PAY" NUMBER(10,2), "POST_TOT" NUMBER(10,2), "TOTAL" NUMBER(10,2), "PRE_RUPEE_CREDIT_EOQ" NUMBER(10,2), "PRE_PCFC_EOQ" NUMBER(10,2), "PRE_TOTAL_EOQ" NUMBER(10,2), "POST_RUPEE_CREDIT_EOQ" NUMBER(10,2), "POST_EBR_EOQ" NUMBER(10,2), "POST_DEF_PAY_EOQ" NUMBER(10,2), "POST_GOV_PAY_EOQ" NUMBER(10,2), "POST_TOT_EOQ" NUMBER(10,2), "TOTAL_EOQ" NUMBER(10,2), "GOLD_CARDS" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_EXP_MFI
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_EXP_MFI" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "FUND_EXP" NUMBER(20,2), "NON_FUND_EXP" NUMBER(20,2), "TOTAL" NUMBER(20,2), "AMT_OUT_FUND" NUMBER(20,2), "AMT_IMPAIRED" NUMBER(20,2), "LOSS_PROVISION" NUMBER(20,2), "MIN_INT" NUMBER(20,2), "MAX_INT" NUMBER(20,2), "WAG_INT" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_GEN_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(100), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_HTMC
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_HTMC" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "FACE_VALUE" NUMBER(10,2), "AQUISITION_COST" NUMBER(10,2), "AMORTISATION" NUMBER(10,2), "AMORTISED_COST" NUMBER(10,2), "PROVISION" NUMBER(10,2), "BOOK_VALUE" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_HTMC2
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_HTMC2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "FACE_VALUE" NUMBER(10,2), "AQUISITION_COST" NUMBER(10,2), "DIMINUTION_OTHER" NUMBER(10,2), "PROVISION" NUMBER(10,2), "BOOK_VALUE" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_HTMC3
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_HTMC3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "FACE_VALUE" NUMBER(10,2), "AQUISITION_COST" NUMBER(10,2), "AMORTISATION_AMT" NUMBER(10,2), "AMORTISED_COST" NUMBER(10,2), "STANDARD" NUMBER(10,2), "SUB_STANDARD" NUMBER(10,2), "DOUBTFUL" NUMBER(10,2), "LOSS" NUMBER(10,2), "PROVISION" NUMBER(10,2), "BOOK_VALUE" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_HTMC4
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_HTMC4" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "FACE_VALUE" NUMBER(10,2), "AQUISITION_COST" NUMBER(10,2), "BOOK_VALUE" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_HTMC5
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_HTMC5" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "FACE_VALUE" NUMBER(10,2), "BOOK_VALUE" NUMBER(10,2), "MARKET_VALUE" NUMBER(10,2), "AGGREGATE_APPRE" NUMBER(10,2), "AGGREGATE_DEPRE" NUMBER(10,2), "AGGREGATE_BOOK_VALUE" NUMBER(10,2), "ADD_PROV" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_HTMC_SC
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_HTMC_SC" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "FACE_VALUE" NUMBER(10,2), "BOOK_VALUE" NUMBER(10,2), "MARKET_VALUE" NUMBER(10,2), "AGGREGATE_APPRE" NUMBER(10,2), "AGGREGATE_DEPRE" NUMBER(10,2), "NET_DEP" NUMBER(10,2), "PROVISION_NET_DEP" NUMBER(10,2), "PROVISION_DEP" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_IMPAIRED_CR
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_IMPAIRED_CR" ("SR_NO" NUMBER, "PAN" VARCHAR2(200), "NAME" VARCHAR2(200), "DATE_SANCTION" VARCHAR2(50), "LOANS_ADVANCES" NUMBER(10,2), "CONTINGENT_CREDITS" NUMBER(10,2), "TCE" NUMBER(10,2), "RISK_CLASS" VARCHAR2(100), "LOSS_PROVISON" NUMBER(10,2), "INTREST_ARREARS" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_IMPAIRED_CR_TOT
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_IMPAIRED_CR_TOT" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "LOANS_ADVANCES" NUMBER(20,4), "CONTINGENT_CREDITS" NUMBER(20,4), "TCE" NUMBER(20,4), "LOSS_PROVISON" NUMBER(20,4), "INTREST_ARREARS" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_INDUS_BRK
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_INDUS_BRK" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "TCE" NUMBER(20,2), "TOT_INVES_EXP" NUMBER(20,2), "TOT_EXP" NUMBER(20,2), "TOT_ADV_OUT" NUMBER(20,2), "STN_ADV" NUMBER(20,2), "GROSS_NPA" NUMBER(20,2), "NEW_ACRETION_NPAS" NUMBER(20,2), "UP_GRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPAS_EOP" NUMBER(20,2), "SUBSTANDARD_ADVANCES" NUMBER(20,2), "DOUBTFUL_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PROVISIONS" NUMBER(20,2), "CUMULATIVE_WOFFS" NUMBER(20,2), "OUTSTANDING_BOOKS_BANK" NUMBER(20,2), "REST_STANDARD_ADVANCES" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_INDUS_BRK2
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_INDUS_BRK2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "TCE" NUMBER(20,2), "TOT_INVES_EXP" NUMBER(20,2), "TOT_EXP" NUMBER(20,2), "TOT_ADV_OUT" NUMBER(20,2), "STN_ADV" NUMBER(20,2), "GROSS_NPA" NUMBER(20,2), "NEW_ACRETION_NPAS" NUMBER(20,2), "UP_GRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPAS_EOP" NUMBER(20,2), "SUBSTANDARD_ADVANCES" NUMBER(20,2), "DOUBTFUL_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PROVISIONS" NUMBER(20,2), "CUMULATIVE_WOFFS" NUMBER(20,2), "OUTSTANDING_BOOKS_BANK" NUMBER(20,2), "REST_STANDARD_ADVANCES" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_INDUS_BRK_A
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_INDUS_BRK_A" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "TCE" NUMBER(20,2), "TOT_INVES_EXP" NUMBER(20,2), "TOT_EXP" NUMBER(20,2), "TOT_ADV_OUT" NUMBER(20,2), "STN_ADV" NUMBER(20,2), "GROSS_NPA" NUMBER(20,2), "NEW_ACRETION_NPAS" NUMBER(20,2), "UP_GRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPAS_EOP" NUMBER(20,2), "SUBSTANDARD_ADVANCES" NUMBER(20,2), "DOUBTFUL_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PROVISIONS" NUMBER(20,2), "CUMULATIVE_WOFFS" NUMBER(20,2), "OUTSTANDING_BOOKS_BANK" NUMBER(20,2), "REST_STANDARD_ADVANCES" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_INDUS_BRK_NONSLR
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_INDUS_BRK_NONSLR" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOMESTIC" NUMBER(20,2), "OVERSEAS" NUMBER(20,2), "GLOBAL" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_INDUS_BRK_SEC8
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_INDUS_BRK_SEC8" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "TCE" NUMBER(20,2), "TOT_INVES_EXP" NUMBER(20,2), "TOT_EXP" NUMBER(20,2), "TOT_ADV_OUT" NUMBER(20,2), "STN_ADV" NUMBER(20,2), "GROSS_NPA" NUMBER(20,2), "NEW_ACRETION_NPAS" NUMBER(20,2), "UP_GRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPAS_EOP" NUMBER(20,2), "SUBSTANDARD_ADVANCES" NUMBER(20,2), "DOUBTFUL_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PROVISIONS" NUMBER(20,2), "CUMULATIVE_WOFFS" NUMBER(20,2), "OUTSTANDING_BOOKS_BANK" NUMBER(20,2), "REST_STANDARD_ADVANCES" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_INDUS_OTH1
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_INDUS_OTH1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "TCE" NUMBER(20,2), "TOT_INVES_EXP" NUMBER(20,2), "TOT_EXP" NUMBER(20,2), "TOT_ADV_OUT" NUMBER(20,2), "STN_ADV" NUMBER(20,2), "GROSS_NPA" NUMBER(20,2), "NEW_ACRETION_NPAS" NUMBER(20,2), "UP_GRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPAS_EOP" NUMBER(20,2), "SUBSTANDARD_ADVANCES" NUMBER(20,2), "DOUBTFUL_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PROVISIONS" NUMBER(20,2), "CUMULATIVE_WOFFS" NUMBER(20,2), "OUTSTANDING_BOOKS_BANK" NUMBER(20,2), "REST_STANDARD_ADVANCES" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_INVEST
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_INVEST" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CURR_QTR_AMT" NUMBER(10,2), "CURR_YR_AMT" NUMBER(10,2), "CURR_TOT_PROV" NUMBER(10,2), "CURR_YR_PROV" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_NON_SLR_SEC
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_NON_SLR_SEC" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "RATING_WISE_RATED" NUMBER(20,2), "RATING_WISE_UNRATED" NUMBER(20,2), "CATE_WISE_BORROWER" NUMBER(20,2), "CATE_WISE_NON_BORROWER" NUMBER(20,2), "AMT_RATED" NUMBER(20,2), "AMT_UNRATED" NUMBER(20,2), "TOT_NPA" NUMBER(20,2), "TOT_PROV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_NON_SLR_SEC_2
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_NON_SLR_SEC_2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "RATING_WISE_RATED" NUMBER(20,2), "RATING_WISE_UNRATED" NUMBER(20,2), "CATE_WISE_BORROWER" NUMBER(20,2), "CATE_WISE_NON_BORROWER" NUMBER(20,2), "AMT_RATED" NUMBER(20,2), "AMT_UNRATED" NUMBER(20,2), "TOT_NPA" NUMBER(20,2), "TOT_PROV" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_PORTFOLIO_PARTA
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_PORTFOLIO_PARTA" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "LOANS" NUMBER(20,2), "REFINANCE" NUMBER(20,2), "BILLS_PURCHASED_DISCOUNTED" NUMBER(20,2), "DEPOSITS_CORPORATE" NUMBER(20,2), "TOTAL_LOAN_ASSETS" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_PORTFOLIO_PARTA_MEMO
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_PORTFOLIO_PARTA_MEMO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "LAST_QTR" VARCHAR2(200), "CUURENT_QTR" VARCHAR2(200), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_PORTFOLIO_PARTB
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_PORTFOLIO_PARTB" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CORPORATES" NUMBER(20,2), "CENTRAL_GOVT" NUMBER(20,2), "STATE_GOVT" NUMBER(20,2), "LEASE" NUMBER(20,2), "OTHERS" NUMBER(20,2), "TOTAL_ASSETS" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_PORTFOLIO_PARTB_GOVSEC
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_PORTFOLIO_PARTB_GOVSEC" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "AMT" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_RESTRUCT_ADV
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_RESTRUCT_ADV" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "ITEM" VARCHAR2(200), "AC_RE_APRIL_TO_DATE" NUMBER(10,2), "THROUGH_CDR" NUMBER(10,2), "AC_RE_EOQ" NUMBER(10,2), "THROUGH_CDR_EOQ" NUMBER(10,2), "RE_AC_NPA" NUMBER(10,2), "RE_AC_NPA_EOQ" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_RESTRUCT_PARTB
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_RESTRUCT_PARTB" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_RESTRUCT_PARTB2
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_RESTRUCT_PARTB2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_RESTRUCT_PARTB3
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_RESTRUCT_PARTB3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_RES_ADV_OTH
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_RES_ADV_OTH" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SECCR2_A_QUA_LOAN
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SECCR2_A_QUA_LOAN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "TOTAL_ADVANCES" NUMBER(20,2), "STANDARD_ADVANCES" NUMBER(20,2), "GROSS_NPAS" NUMBER(20,2), "NEW_ACRETION_NPAS" NUMBER(20,2), "UP_GRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPAS_EOP" NUMBER(20,2), "SUBSTANDARD_ADVANCES" NUMBER(20,2), "DOUBTFUL_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PROVISIONS" NUMBER(20,2), "CUMULATIVE_WOFFS" NUMBER(20,2), "OUTSTANDING_BOOKS_BANK" NUMBER(20,2), "REST_STANDARD_ADVANCES" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SECCR3_A_QUA_LOAN
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SECCR3_A_QUA_LOAN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "TOTAL_ADVANCES" NUMBER(20,2), "STANDARD_ADVANCES" NUMBER(20,2), "GROSS_NPAS" NUMBER(20,2), "NEW_ACRETION_NPAS" NUMBER(20,2), "UP_GRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPAS_EOP" NUMBER(20,2), "SUBSTANDARD_ADVANCES" NUMBER(20,2), "DOUBTFUL_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PROVISIONS" NUMBER(20,2), "CUMULATIVE_WOFFS" NUMBER(20,2), "OUTSTANDING_BOOKS_BANK" NUMBER(20,2), "REST_STANDARD_ADVANCES" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SECCR4_A_QUA_LOAN
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SECCR4_A_QUA_LOAN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "TOTAL_ADVANCES" NUMBER(20,2), "STANDARD_ADVANCES" NUMBER(20,2), "GROSS_NPAS" NUMBER(20,2), "NEW_ACRETION_NPAS" NUMBER(20,2), "UP_GRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPAS_EOP" NUMBER(20,2), "SUBSTANDARD_ADVANCES" NUMBER(20,2), "DOUBTFUL_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PROVISIONS" NUMBER(20,2), "CUMULATIVE_WOFFS" NUMBER(20,2), "OUTSTANDING_BOOKS_BANK" NUMBER(20,2), "REST_STANDARD_ADVANCES" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SECCR5_A_QUA_LOAN
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SECCR5_A_QUA_LOAN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "TOTAL_ADVANCES" NUMBER(20,2), "STANDARD_ADVANCES" NUMBER(20,2), "GROSS_NPAS" NUMBER(20,2), "NEW_ACRETION_NPAS" NUMBER(20,2), "UP_GRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPAS_EOP" NUMBER(20,2), "SUBSTANDARD_ADVANCES" NUMBER(20,2), "DOUBTFUL_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PROVISIONS" NUMBER(20,2), "CUMULATIVE_WOFFS" NUMBER(20,2), "OUTSTANDING_BOOKS_BANK" NUMBER(20,2), "REST_STANDARD_ADVANCES" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SECCR6_A_QUA_LOAN
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SECCR6_A_QUA_LOAN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "TOTAL_ADVANCES" NUMBER(20,2), "STANDARD_ADVANCES" NUMBER(20,2), "GROSS_NPAS" NUMBER(20,2), "NEW_ACRETION_NPAS" NUMBER(20,2), "UP_GRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPAS_EOP" NUMBER(20,2), "SUBSTANDARD_ADVANCES" NUMBER(20,2), "DOUBTFUL_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PROVISIONS" NUMBER(20,2), "CUMULATIVE_WOFFS" NUMBER(20,2), "OUTSTANDING_BOOKS_BANK" NUMBER(20,2), "REST_STANDARD_ADVANCES" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SECCR7_A_QUA_LOAN
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SECCR7_A_QUA_LOAN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "TOTAL_ADVANCES" NUMBER(20,2), "STANDARD_ADVANCES" NUMBER(20,2), "GROSS_NPAS" NUMBER(20,2), "NEW_ACRETION_NPAS" NUMBER(20,2), "UP_GRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPAS_EOP" NUMBER(20,2), "SUBSTANDARD_ADVANCES" NUMBER(20,2), "DOUBTFUL_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PROVISIONS" NUMBER(20,2), "CUMULATIVE_WOFFS" NUMBER(20,2), "OUTSTANDING_BOOKS_BANK" NUMBER(20,2), "REST_STANDARD_ADVANCES" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SECCR_A1
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SECCR_A1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "TOTAL_ADVANCES" NUMBER(20,2), "STANDARD_ADVANCES" NUMBER(20,2), "GROSS_NPAS" NUMBER(20,2), "NEW_ACRETION_NPAS" NUMBER(20,2), "UP_GRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPAS_EOP" NUMBER(20,2), "SUBSTANDARD_ADVANCES" NUMBER(20,2), "DOUBTFUL_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PROVISIONS" NUMBER(20,2), "CUMULATIVE_WOFFS" NUMBER(20,2), "OUTSTANDING_BOOKS_BANK" NUMBER(20,2), "REST_STANDARD_ADVANCES" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SECCR_A2
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SECCR_A2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "TOTAL_ADVANCES" NUMBER(20,2), "STANDARD_ADVANCES" NUMBER(20,2), "GROSS_NPAS" NUMBER(20,2), "NEW_ACRETION_NPAS" NUMBER(20,2), "UP_GRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPAS_EOP" NUMBER(20,2), "SUBSTANDARD_ADVANCES" NUMBER(20,2), "DOUBTFUL_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PROVISIONS" NUMBER(20,2), "CUMULATIVE_WOFFS" NUMBER(20,2), "OUTSTANDING_BOOKS_BANK" NUMBER(20,2), "REST_STANDARD_ADVANCES" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SECCR_A3
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SECCR_A3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "TOTAL_ADVANCES" NUMBER(20,2), "STANDARD_ADVANCES" NUMBER(20,2), "GROSS_NPAS" NUMBER(20,2), "NEW_ACRETION_NPAS" NUMBER(20,2), "UP_GRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPAS_EOP" NUMBER(20,2), "SUBSTANDARD_ADVANCES" NUMBER(20,2), "DOUBTFUL_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PROVISIONS" NUMBER(20,2), "CUMULATIVE_WOFFS" NUMBER(20,2), "OUTSTANDING_BOOKS_BANK" NUMBER(20,2), "REST_STANDARD_ADVANCES" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SECCR_A4
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SECCR_A4" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "TOTAL_ADVANCES" NUMBER(20,2), "STANDARD_ADVANCES" NUMBER(20,2), "GROSS_NPAS" NUMBER(20,2), "NEW_ACRETION_NPAS" NUMBER(20,2), "UP_GRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPAS_EOP" NUMBER(20,2), "SUBSTANDARD_ADVANCES" NUMBER(20,2), "DOUBTFUL_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PROVISIONS" NUMBER(20,2), "CUMULATIVE_WOFFS" NUMBER(20,2), "OUTSTANDING_BOOKS_BANK" NUMBER(20,2), "REST_STANDARD_ADVANCES" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SECCR_A5
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SECCR_A5" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "TOTAL_ADVANCES" NUMBER(20,2), "STANDARD_ADVANCES" NUMBER(20,2), "GROSS_NPAS" NUMBER(20,2), "NEW_ACRETION_NPAS" NUMBER(20,2), "UP_GRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPAS_EOP" NUMBER(20,2), "SUBSTANDARD_ADVANCES" NUMBER(20,2), "DOUBTFUL_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PROVISIONS" NUMBER(20,2), "CUMULATIVE_WOFFS" NUMBER(20,2), "OUTSTANDING_BOOKS_BANK" NUMBER(20,2), "REST_STANDARD_ADVANCES" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SECCR_A6
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SECCR_A6" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "TOTAL_ADVANCES" NUMBER(20,2), "STANDARD_ADVANCES" NUMBER(20,2), "GROSS_NPAS" NUMBER(20,2), "NEW_ACRETION_NPAS" NUMBER(20,2), "UP_GRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPAS_EOP" NUMBER(20,2), "SUBSTANDARD_ADVANCES" NUMBER(20,2), "DOUBTFUL_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PROVISIONS" NUMBER(20,2), "CUMULATIVE_WOFFS" NUMBER(20,2), "OUTSTANDING_BOOKS_BANK" NUMBER(20,2), "REST_STANDARD_ADVANCES" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SECCR_A7
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SECCR_A7" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "TOTAL_ADVANCES" NUMBER(20,2), "STANDARD_ADVANCES" NUMBER(20,2), "GROSS_NPAS" NUMBER(20,2), "NEW_ACRETION_NPAS" NUMBER(20,2), "UP_GRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPAS_EOP" NUMBER(20,2), "SUBSTANDARD_ADVANCES" NUMBER(20,2), "DOUBTFUL_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PROVISIONS" NUMBER(20,2), "CUMULATIVE_WOFFS" NUMBER(20,2), "OUTSTANDING_BOOKS_BANK" NUMBER(20,2), "REST_STANDARD_ADVANCES" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SECCR_A8
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SECCR_A8" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "TOTAL_ADVANCES" NUMBER(20,2), "STANDARD_ADVANCES" NUMBER(20,2), "GROSS_NPAS" NUMBER(20,2), "NEW_ACRETION_NPAS" NUMBER(20,2), "UP_GRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPAS_EOP" NUMBER(20,2), "SUBSTANDARD_ADVANCES" NUMBER(20,2), "DOUBTFUL_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PROVISIONS" NUMBER(20,2), "CUMULATIVE_WOFFS" NUMBER(20,2), "OUTSTANDING_BOOKS_BANK" NUMBER(20,2), "REST_STANDARD_ADVANCES" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SECCR_A9
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SECCR_A9" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "TOTAL_ADVANCES" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SECCR_A_QUA_LOAN
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SECCR_A_QUA_LOAN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "TOTAL_ADVANCES" NUMBER(20,2), "STANDARD_ADVANCES" NUMBER(20,2), "GROSS_NPAS" NUMBER(20,2), "NEW_ACRETION_NPAS" NUMBER(20,2), "UP_GRADATION" NUMBER(20,2), "ACTUAL_RECOVERIES" NUMBER(20,2), "WRITE_OFFS" NUMBER(20,2), "REDUCTION" NUMBER(20,2), "GROSS_NPAS_EOP" NUMBER(20,2), "SUBSTANDARD_ADVANCES" NUMBER(20,2), "DOUBTFUL_ADVANCES" NUMBER(20,2), "LOSS_ADVANCES" NUMBER(20,2), "TOT_LOSS_PROVISIONS" NUMBER(20,2), "CUMULATIVE_WOFFS" NUMBER(20,2), "OUTSTANDING_BOOKS_BANK" NUMBER(20,2), "REST_STANDARD_ADVANCES" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SECPORTFOLIO
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SECPORTFOLIO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "BOOK_MATURITY" NUMBER(10,2), "BOOK_SALE" NUMBER(10,2), "BOOK_TRADING" NUMBER(10,2), "BOOK_TOTAL" NUMBER(10,2), "MARKET_MATURITY" NUMBER(10,2), "MARKET_SALE" NUMBER(10,2), "MARKET_TRADE" NUMBER(10,2), "MARKET_TOTAL" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SEN_RISK
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SEN_RISK" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOM_EXP" NUMBER(20,2), "DOM_GROSS_OUT" NUMBER(20,2), "DOM_IMPAIR" NUMBER(20,2), "OVER_EXP" NUMBER(20,2), "OVER_GROSS_OUT" NUMBER(20,2), "OVER_IMPAIR" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SEN_RISK2
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SEN_RISK2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOM_EXP" NUMBER(20,2), "DOM_GROSS_OUT" NUMBER(20,2), "DOM_IMPAIR" NUMBER(20,2), "OVER_EXP" NUMBER(20,2), "OVER_GROSS_OUT" NUMBER(20,2), "OVER_IMPAIR" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SEN_RISK3
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SEN_RISK3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOM_EXP" NUMBER(20,2), "DOM_GROSS_OUT" NUMBER(20,2), "DOM_IMPAIR" NUMBER(20,2), "OVER_EXP" NUMBER(20,2), "OVER_GROSS_OUT" NUMBER(20,2), "OVER_IMPAIR" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SEN_RISK4
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SEN_RISK4" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOM_EXP" NUMBER(20,2), "DOM_GROSS_OUT" NUMBER(20,2), "DOM_IMPAIR" NUMBER(20,2), "OVER_EXP" NUMBER(20,2), "OVER_GROSS_OUT" NUMBER(20,2), "OVER_IMPAIR" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SEN_SEC1
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SEN_SEC1" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOM_EXP" NUMBER(20,2), "DOM_GROSS_OUT" NUMBER(20,2), "DOM_IMPAIR" NUMBER(20,2), "OVER_EXP" NUMBER(20,2), "OVER_GROSS_OUT" NUMBER(20,2), "OVER_IMPAIR" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SEN_SEC2
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SEN_SEC2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOM_EXP" NUMBER(20,2), "DOM_GROSS_OUT" NUMBER(20,2), "DOM_IMPAIR" NUMBER(20,2), "OVER_EXP" NUMBER(20,2), "OVER_GROSS_OUT" NUMBER(20,2), "OVER_IMPAIR" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SEN_SEC3
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SEN_SEC3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOM_EXP" NUMBER(20,2), "DOM_GROSS_OUT" NUMBER(20,2), "DOM_IMPAIR" NUMBER(20,2), "OVER_EXP" NUMBER(20,2), "OVER_GROSS_OUT" NUMBER(20,2), "OVER_IMPAIR" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SEN_SECB
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SEN_SECB" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOM_TOT_EXP" NUMBER(20,2), "DOM_AMT_OUT" NUMBER(20,2), "DOM_RESTR" NUMBER(20,2), "DOM_IMPAIR" NUMBER(20,2), "DOM_SLIP_TOT_STND" NUMBER(20,2), "OVR_TOT_EXP" NUMBER(20,2), "OVR_AMT_OUT" NUMBER(20,2), "OVR_RESTR" NUMBER(20,2), "OVR_IMPAIR" NUMBER(20,2), "OVR_SLIP_TOT_STND" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SEN_SECB2
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SEN_SECB2" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOM_TOT_EXP" NUMBER(20,2), "DOM_AMT_OUT" NUMBER(20,2), "DOM_RESTR" NUMBER(20,2), "DOM_IMPAIR" NUMBER(20,2), "DOM_SLIP_TOT_STND" NUMBER(20,2), "OVR_TOT_EXP" NUMBER(20,2), "OVR_AMT_OUT" NUMBER(20,2), "OVR_RESTR" NUMBER(20,2), "OVR_IMPAIR" NUMBER(20,2), "OVR_SLIP_TOT_STND" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SEN_SECB2_TOT
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SEN_SECB2_TOT" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOM_TOT_EXP" NUMBER(20,2), "DOM_AMT_OUT" NUMBER(20,2), "DOM_RESTR" NUMBER(20,2), "DOM_IMPAIR" NUMBER(20,2), "DOM_SLIP_TOT_STND" NUMBER(20,2), "OVR_TOT_EXP" NUMBER(20,2), "OVR_AMT_OUT" NUMBER(20,2), "OVR_RESTR" NUMBER(20,2), "OVR_IMPAIR" NUMBER(20,2), "OVR_SLIP_TOT_STND" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SEN_SECB3
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SEN_SECB3" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOM_TOT_EXP" NUMBER(20,2), "DOM_AMT_OUT" NUMBER(20,2), "DOM_RESTR" NUMBER(20,2), "DOM_IMPAIR" NUMBER(20,2), "DOM_SLIP_TOT_STND" NUMBER(20,2), "OVR_TOT_EXP" NUMBER(20,2), "OVR_AMT_OUT" NUMBER(20,2), "OVR_RESTR" NUMBER(20,2), "OVR_IMPAIR" NUMBER(20,2), "OVR_SLIP_TOT_STND" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SEN_SECB3_TOT
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SEN_SECB3_TOT" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOM_TOT_EXP" NUMBER(20,2), "DOM_AMT_OUT" NUMBER(20,2), "DOM_RESTR" NUMBER(20,2), "DOM_IMPAIR" NUMBER(20,2), "DOM_SLIP_TOT_STND" NUMBER(20,2), "OVR_TOT_EXP" NUMBER(20,2), "OVR_AMT_OUT" NUMBER(20,2), "OVR_RESTR" NUMBER(20,2), "OVR_IMPAIR" NUMBER(20,2), "OVR_SLIP_TOT_STND" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SEN_SECB4
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SEN_SECB4" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOM_TOT_EXP" NUMBER(20,2), "DOM_AMT_OUT" NUMBER(20,2), "DOM_RESTR" NUMBER(20,2), "DOM_IMPAIR" NUMBER(20,2), "DOM_SLIP_TOT_STND" NUMBER(20,2), "OVR_TOT_EXP" NUMBER(20,2), "OVR_AMT_OUT" NUMBER(20,2), "OVR_RESTR" NUMBER(20,2), "OVR_IMPAIR" NUMBER(20,2), "OVR_SLIP_TOT_STND" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SEN_SECB4_TOT
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SEN_SECB4_TOT" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOM_TOT_EXP" NUMBER(20,2), "DOM_AMT_OUT" NUMBER(20,2), "DOM_RESTR" NUMBER(20,2), "DOM_IMPAIR" NUMBER(20,2), "DOM_SLIP_TOT_STND" NUMBER(20,2), "OVR_TOT_EXP" NUMBER(20,2), "OVR_AMT_OUT" NUMBER(20,2), "OVR_RESTR" NUMBER(20,2), "OVR_IMPAIR" NUMBER(20,2), "OVR_SLIP_TOT_STND" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SEN_SECB5
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SEN_SECB5" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOM_TOT_EXP" NUMBER(20,2), "DOM_AMT_OUT" NUMBER(20,2), "DOM_RESTR" NUMBER(20,2), "DOM_IMPAIR" NUMBER(20,2), "DOM_SLIP_TOT_STND" NUMBER(20,2), "OVR_TOT_EXP" NUMBER(20,2), "OVR_AMT_OUT" NUMBER(20,2), "OVR_RESTR" NUMBER(20,2), "OVR_IMPAIR" NUMBER(20,2), "OVR_SLIP_TOT_STND" NUMBER(20,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SEN_SECB_TOT
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SEN_SECB_TOT" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "DOM_TOT_EXP" NUMBER(20,2), "DOM_AMT_OUT" NUMBER(20,2), "DOM_RESTR" NUMBER(20,2), "DOM_IMPAIR" NUMBER(20,2), "DOM_SLIP_TOT_STND" NUMBER(20,2), "OVR_TOT_EXP" NUMBER(20,2), "OVR_AMT_OUT" NUMBER(20,2), "OVR_RESTR" NUMBER(20,2), "OVR_IMPAIR" NUMBER(20,2), "OVR_SLIP_TOT_STND" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RAQ_SIGN
--------------------------------------------------------

  CREATE TABLE "FIMD_RAQ_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RCA1_CAPITAL_BASE
--------------------------------------------------------

  CREATE TABLE "FIMD_RCA1_CAPITAL_BASE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "AMOUNT" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RCA1_COMPUTATION_CAP_BASE
--------------------------------------------------------

  CREATE TABLE "FIMD_RCA1_COMPUTATION_CAP_BASE" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "AMOUNT" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RCA1_COMPUTATION_CAP_OTH1
--------------------------------------------------------

  CREATE TABLE "FIMD_RCA1_COMPUTATION_CAP_OTH1" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(200), "AMOUNT" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RCA1_COMPUTATION_CAP_OTH2
--------------------------------------------------------

  CREATE TABLE "FIMD_RCA1_COMPUTATION_CAP_OTH2" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(200), "AMOUNT" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RCA1_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "FIMD_RCA1_GEN_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RCA1_GLOBAL_ENDQTR
--------------------------------------------------------

  CREATE TABLE "FIMD_RCA1_GLOBAL_ENDQTR" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "AMOUNT" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RCA1_RWAE_SECA
--------------------------------------------------------

  CREATE TABLE "FIMD_RCA1_RWAE_SECA" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "BOOK_VALUE" NUMBER(10,2), "UNDER_BANKING_BOOK" NUMBER(10,2), "MARGINS_PROVISION" NUMBER(10,2), "BOOK_VALUE_NET" NUMBER(10,2), "RISK_WEIGHT" NUMBER(10,2), "RISK_ADJ_VAL" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RCA1_RWAE_SECB
--------------------------------------------------------

  CREATE TABLE "FIMD_RCA1_RWAE_SECB" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "GUARANTOR_GP" VARCHAR2(100), "TOTAL_BOOK_EXP" NUMBER(10,2), "MARGINS_PROVISION" NUMBER(10,2), "BOOK_EXPOSURE" NUMBER(10,2), "CCF_CONTIGENCY" NUMBER(20,4), "RW_OBLIGANT" NUMBER(10,2), "RAV_EXPOSURE" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RCA1_RWAE_SECC
--------------------------------------------------------

  CREATE TABLE "FIMD_RCA1_RWAE_SECC" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "CREDITEXP_CONVER_FACT" NUMBER(20,4), "COUNTER_PARTY_CLIENT" VARCHAR2(100), "NAT_PRINC_AMNT" NUMBER(10,2), "POTENT_EXP" NUMBER(10,2), "REPLAC_COST" NUMBER(10,2), "CURR_EXP" NUMBER(10,2), "CRED_EQUI_AMNT" NUMBER(10,2), "RISK_WEIGHT" NUMBER(10,2), "RISK_ADJ_VAL" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RCA1_RWATRBK_SECD
--------------------------------------------------------

  CREATE TABLE "FIMD_RCA1_RWATRBK_SECD" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "AMOUNT" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RCA1_SECD_OTH1
--------------------------------------------------------

  CREATE TABLE "FIMD_RCA1_SECD_OTH1" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(200), "AMOUNT" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RCA1_SECD_OTH2
--------------------------------------------------------

  CREATE TABLE "FIMD_RCA1_SECD_OTH2" ("SR_NO" NUMBER, "PARTICULAR" VARCHAR2(200), "AMOUNT" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RCA1_SIGNATORY
--------------------------------------------------------

  CREATE TABLE "FIMD_RCA1_SIGNATORY" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "AUTH_REP_OFFICI" VARCHAR2(100), "COUNTERSIGNED_BY" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RCA1_UNDISCLOSED_RES
--------------------------------------------------------

  CREATE TABLE "FIMD_RCA1_UNDISCLOSED_RES" ("SR_NO" NUMBER, "ACCOUNT_NAME" VARCHAR2(200), "AMOUNT" NUMBER(10,2), "GROUP_NAME" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RCL_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "FIMD_RCL_GEN_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RCL_SECA_TOTAL
--------------------------------------------------------

  CREATE TABLE "FIMD_RCL_SECA_TOTAL" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RCL_SECTIONA_1
--------------------------------------------------------

  CREATE TABLE "FIMD_RCL_SECTIONA_1" ("SR_NO" NUMBER, "NAME_SUBDIARY" VARCHAR2(200), "TOAL_PAID_CAP" NUMBER(10,2), "PER_SHAR_HELD" NUMBER(20,4), "MJR_ACTIVITY" VARCHAR2(100), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table FIMD_RCL_SECTIONA_2
--------------------------------------------------------

  CREATE TABLE "FIMD_RCL_SECTIONA_2" ("SR_NO" NUMBER, "NAME_FI_SUBDIARY" VARCHAR2(200), "TYPE_EXPOSER" VARCHAR2(100), "AMNT_CREDIT" NUMBER(10,2), "AMNT_OUT" NUMBER(10,2), "ASSET_CLASSF" VARCHAR2(100), "PROVISION_HELD" NUMBER(10,2), "CREDIT_EXPOSURE" NUMBER(20,4), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table FIMD_RCL_SECTIONC_PARTA
--------------------------------------------------------

  CREATE TABLE "FIMD_RCL_SECTIONC_PARTA" ("SR_NO" NUMBER, "NAME_ASS_DIREC" VARCHAR2(200), "TYPE_FI_EXP" VARCHAR2(100), "AMOUNT_FI_" NUMBER(10,2), "TERM_CRED_EXP" VARCHAR2(100), "VAL_SEC" NUMBER(10,2), "ASSET_CLASS" VARCHAR2(100), "PROV_HELD" NUMBER(10,2), "UNIQUE_TRANS_CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RCL_SECTIONC_PARTB
--------------------------------------------------------

  CREATE TABLE "FIMD_RCL_SECTIONC_PARTB" ("SR_NO" NUMBER, "NAME_DIREC" VARCHAR2(200), "NAME_INTRES_DIRE" VARCHAR2(200), "NATURE_INTREST" VARCHAR2(200), "TYPE_FI_EXPSR" VARCHAR2(200), "AMNT_FI_EXPSR" NUMBER(10,2), "TERM_CREDIT" VARCHAR2(200), "VAL_SECURITIES" NUMBER(10,2), "ASSET_CLASS" VARCHAR2(200), "PROV_HELD" NUMBER(10,2), "UNIQUE_TRANS_CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RCL_SECTION_B
--------------------------------------------------------

  CREATE TABLE "FIMD_RCL_SECTION_B" ("SR_NO" NUMBER, "NAME_SHAREHOLDER" VARCHAR2(200), "NATURE_INTREST" VARCHAR2(100), "TYPE_EXPOSER" VARCHAR2(100), "AMNT_EXP_FUND" NUMBER(10,2), "AMNT_EXP_NONFUND" NUMBER(10,2), "TERM_CREDIT_EXP" VARCHAR2(100), "VAL_SECURITIES" NUMBER(10,2), "ASSET_CLASS" VARCHAR2(100), "PROV_HELD" NUMBER(10,2), "UNIQUE_TRANS_CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RCL_SIGNATORIES
--------------------------------------------------------

  CREATE TABLE "FIMD_RCL_SIGNATORIES" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "AUTH_REP_OFFICI" VARCHAR2(100), "COUNTERSIGNED_BY" VARCHAR2(100), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_CAPITAL_FUND
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_CAPITAL_FUND" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "VALUE" NUMBER(10,2), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_GEN_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SEC_A
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SEC_A" ("SR_NO" NUMBER(20,4), "PAN" VARCHAR2(100), "CUSTOMER_NAME" VARCHAR2(1000), "INDUSTRY_CODE" VARCHAR2(1000), "INDUSTRY_NAME" VARCHAR2(1000), "SECTOR_CODE" VARCHAR2(1000), "BANKING_ARRANGEMENT" VARCHAR2(1000), "LEAD_BANK_CODE" VARCHAR2(1000), "INTERNAL_RATING" VARCHAR2(1000), "EXTERNAL_RATING" VARCHAR2(1000), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "FUNDED_INFRA" NUMBER(20,2), "FUNDED_INFRA_OTHER" NUMBER(20,2), "TOTAL_FUNDED_CREDIT_EXP" NUMBER(20,2), "NON_FUNDED_INFRA" NUMBER(20,2), "NON_FUNDED_INFRA_OTHER" NUMBER(20,2), "NON_FUNDED_CREDIT_EXP" NUMBER(20,2), "TOTAL_INFRA" NUMBER(20,2), "TOTAL_OTHER_INFRA" NUMBER(20,2), "TOTAL_CREDIT_EXP" NUMBER(20,2), "TCE_PER_CAP_FUND_INFRA" NUMBER(20,4), "TCE_PER_CAP_FUND_OTHER_INFRA" NUMBER(20,4), "TCE_PER_CAP_FUND_TOTAL" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SEC_A_TOT
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SEC_A_TOT" ("FUNDED_INFRA" NUMBER(20,2), "FUNDED_INFRA_OTHER" NUMBER(20,2), "TOTAL_FUNDED_CREDIT_EXP" NUMBER(20,2), "NON_FUNDED_INFRA" NUMBER(20,2), "NON_FUNDED_INFRA_OTHER" NUMBER(20,2), "NON_FUNDED_CREDIT_EXP" NUMBER(20,2), "TOTAL_INFRA" NUMBER(20,2), "TOTAL_OTHER_INFRA" NUMBER(20,2), "TOTAL_CREDIT_EXP" NUMBER(20,2), "TCE_PER_CAP_FUND_INFRA" NUMBER(20,4), "TCE_PER_CAP_FUND_OTHER_INFRA" NUMBER(20,4), "TCE_PER_CAP_FUND_TOTAL" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SEC_B
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SEC_B" ("SR_NO" NUMBER, "GROUP_PAN" VARCHAR2(500), "BORROWER_GROUP_NAME" VARCHAR2(500), "PAN" VARCHAR2(20), "CONSTITUENT_NAME" VARCHAR2(1000), "INDUSTRY_CODE" VARCHAR2(1000), "INDUSTRY_NAME" VARCHAR2(1000), "SECTOR_CODE" VARCHAR2(1000), "BANKING_ARRANGEMENT" VARCHAR2(1000), "LEAD_BANK_NAME" VARCHAR2(1000), "INTERNAL_RATING" VARCHAR2(1000), "EXTERNAL_RATING" VARCHAR2(1000), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "FUNDED_INFRA" NUMBER(20,2), "FUNDED_INFRA_OTHER" NUMBER(20,2), "TOTAL_FUNDED_CREDIT_EXP" NUMBER(20,2), "NON_FUNDED_INFRA" NUMBER(20,2), "NON_FUNDED_INFRA_OTHER" NUMBER(20,2), "NON_FUNDED_CREDIT_EXP" NUMBER(20,2), "TOTAL_INFRA" NUMBER(20,2), "TOTAL_OTHER_INFRA" NUMBER(20,2), "TOTAL_CREDIT_EXP" NUMBER(20,2), "TCE_PER_CAP_FUND_INFRA" NUMBER(20,4), "TCE_PER_CAP_FUND_OTHER_INFRA" NUMBER(20,4), "TCE_PER_CAP_FUND_TOTAL" NUMBER(20,4), "TRANSACTION" VARCHAR2(1000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SEC_B_T
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SEC_B_T" ("SR_NO" NUMBER, "GROUP_PAN" VARCHAR2(500), "BORROWER_GROUP_NAME" VARCHAR2(500), "FUNDED_INFRA" NUMBER(20,2), "FUNDED_INFRA_OTHER" NUMBER(20,2), "TOTAL_FUNDED_CREDIT_EXP" NUMBER(20,2), "NON_FUNDED_INFRA" NUMBER(20,2), "NON_FUNDED_INFRA_OTHER" NUMBER(20,2), "NON_FUNDED_CREDIT_EXP" NUMBER(20,2), "TOTAL_INFRA" NUMBER(20,2), "TOTAL_OTHER_INFRA" NUMBER(20,2), "TOTAL_CREDIT_EXP" NUMBER(20,2), "TCE_PER_CAP_FUND_INFRA" NUMBER(20,4), "TCE_PER_CAP_FUND_OTHER_INFRA" NUMBER(20,4), "TCE_PER_CAP_FUND_TOTAL" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SEC_B_TOT
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SEC_B_TOT" ("SR_NO" NUMBER, "GROUP_PAN" VARCHAR2(500), "GRP_BORROWER_NAME" VARCHAR2(500), "FUNDED_INFRA" NUMBER(20,2), "FUNDED_INFRA_OTHER" NUMBER(20,2), "TOTAL_FUNDED_CREDIT_EXP" NUMBER(20,2), "NON_FUNDED_INFRA" NUMBER(20,2), "NON_FUNDED_INFRA_OTHER" NUMBER(20,2), "NON_FUNDED_CREDIT_EXP" NUMBER(20,2), "TOTAL_INFRA" NUMBER(20,2), "TOTAL_OTHER_INFRA" NUMBER(20,2), "TOTAL_CREDIT_EXP" NUMBER(20,2), "TCE_PER_CAP_FUND_INFRA" NUMBER(20,4), "TCE_PER_CAP_FUND_OTHER_INFRA" NUMBER(20,4), "TCE_PER_CAP_FUND_TOTAL" NUMBER(20,4), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SEC_C_CAP
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SEC_C_CAP" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "VALUE" VARCHAR2(500), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SEC_C_CAP_FUND
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SEC_C_CAP_FUND" ("SR_NO" NUMBER, "CAPITAL_FUND_FI" VARCHAR2(500), "AMT_IN_LAKHS" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SEC_C_FOR
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SEC_C_FOR" ("SR_NO" NUMBER, "COUNTER_BANK_NAME" VARCHAR2(500), "COUNTER_BANK_DOMICILE" VARCHAR2(1000), "FUNDED_EXP" NUMBER(20,2), "NONFUND_EXP" NUMBER(20,2), "TOTAL_CRED_EXP" NUMBER(20,2), "TE_CAP_FUND" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SEC_C_FOREIGN
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SEC_C_FOREIGN" ("SR_NO" NUMBER, "CUNTR_PARTY_BK_NAME" VARCHAR2(500), "CUNTR_PARTY_BK_DOMICILE" VARCHAR2(500), "FUNDED_EXP" NUMBER(20,2), "NON_FUNDED_EXP" NUMBER(20,2), "TOTAL_EXP" NUMBER(20,2), "TE_CAPITAL_FUND" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SEC_C_FOREIGN_TOT
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SEC_C_FOREIGN_TOT" ("SR_NO" NUMBER, "FUNDED_EXP" NUMBER(20,2), "NON_FUNDED_EXP" NUMBER(20,2), "TOTAL_EXP" NUMBER(20,2), "TE_CAPITAL_FUND" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SEC_C_FOR_TOT
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SEC_C_FOR_TOT" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "FUNDED_EXP" NUMBER(20,2), "NONFUND_EXP" NUMBER(20,2), "TOTAL_CRED_EXP" NUMBER(20,2), "TE_CAP_FUND" NUMBER(20,4), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SEC_C_GLOB
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SEC_C_GLOB" ("SR_NO" NUMBER, "COUNTER_BANK_NAME" VARCHAR2(500), "COUNTER_BANK_DOMICILE" VARCHAR2(1000), "FUNDED_EXP" NUMBER(20,2), "NONFUND_EXP" NUMBER(20,2), "TOTAL_CRED_EXP" NUMBER(20,2), "TE_CAP_FUND" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SEC_C_GLOBAL
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SEC_C_GLOBAL" ("SR_NO" NUMBER, "CUNTR_PARTY_BK_NAME" VARCHAR2(500), "CUNTR_PARTY_BK_DOMICILE" VARCHAR2(500), "FUNDED_EXP" NUMBER(20,2), "NON_FUNDED_EXP" NUMBER(20,2), "TOTAL_EXP" NUMBER(20,2), "TE_CAPITAL_FUND" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SEC_C_GLOBAL_TOT
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SEC_C_GLOBAL_TOT" ("SR_NO" NUMBER, "FUNDED_EXP" NUMBER(20,2), "NON_FUNDED_EXP" NUMBER(20,2), "TOTAL_EXP" NUMBER(20,2), "TE_CAPITAL_FUND" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SEC_C_GLOB_TOT
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SEC_C_GLOB_TOT" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "FUNDED_EXP" NUMBER(20,2), "NONFUND_EXP" NUMBER(20,2), "TOTAL_CRED_EXP" NUMBER(20,2), "TE_CAP_FUND" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SEC_C_TOP20
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SEC_C_TOP20" ("SR_NO" NUMBER, "COUNTER_BANK_NAME" VARCHAR2(500), "COUNTER_BANK_DOMICILE" VARCHAR2(1000), "FUNDED_EXP" NUMBER(20,2), "NONFUND_EXP" NUMBER(20,2), "TOTAL_CRED_EXP" NUMBER(20,2), "TE_CAP_FUND" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SEC_C_TOP20_EXP
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SEC_C_TOP20_EXP" ("SR_NO" NUMBER, "CUNTR_PARTY_BK_NAME" VARCHAR2(500), "CUNTR_PARTY_BK_DOMICILE" VARCHAR2(500), "FUNDED_EXP" NUMBER(20,2), "NON_FUNDED_EXP" NUMBER(20,2), "TOTAL_EXP" NUMBER(20,2), "TE_CAPITAL_FUND" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SEC_C_TOP20_EXP_TOT
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SEC_C_TOP20_EXP_TOT" ("SR_NO" NUMBER, "FUNDED_EXP" NUMBER(20,2), "NON_FUNDED_EXP" NUMBER(20,2), "TOTAL_EXP" NUMBER(20,2), "TE_CAPITAL_FUND" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SEC_C_TOP20_FI
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SEC_C_TOP20_FI" ("SR_NO" NUMBER, "CUNTR_PARTY_BK_NAME" VARCHAR2(500), "CUNTR_PARTY_BK_DOMICILE" VARCHAR2(500), "FUNDED_EXP" NUMBER(20,2), "NON_FUNDED_EXP" NUMBER(20,2), "TOTAL_EXP" NUMBER(20,2), "TE_CAPITAL_FUND" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SEC_C_TOP20_FI_TOT
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SEC_C_TOP20_FI_TOT" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "FUNDED_EXP" NUMBER(20,2), "NONFUND_EXP" NUMBER(20,2), "TOTAL_CRED_EXP" NUMBER(20,2), "TE_CAP_FUND" NUMBER(20,4), "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SEC_C_TOP20_TOT
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SEC_C_TOP20_TOT" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "FUNDED_EXP" NUMBER(20,2), "NONFUND_EXP" NUMBER(20,2), "TOTAL_CRED_EXP" NUMBER(20,2), "TE_CAP_FUND" NUMBER(20,4), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table FIMD_RLC_SIGN
--------------------------------------------------------

  CREATE TABLE "FIMD_RLC_SIGN" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(500), "AUTHORISED_SIGN" VARCHAR2(500), "COUNTER_SIGN" VARCHAR2(500), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table FIMD_ROC_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "FIMD_ROC_GEN_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_ROC_SEC1_PARTA_OWENERSHIP
--------------------------------------------------------

  CREATE TABLE "FIMD_ROC_SEC1_PARTA_OWENERSHIP" ("SR_NO" NUMBER, "NAME" VARCHAR2(200), "STATUS_CODE" VARCHAR2(100), "SHARES_HELD" NUMBER(10,2), "SHARES_IN_TOTAL" NUMBER(20,4), "BOOK_VALUE_SH" NUMBER(10,2), "FACE_VALUE_SH" NUMBER(10,2), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table FIMD_ROC_SEC1_PARTB
--------------------------------------------------------

  CREATE TABLE "FIMD_ROC_SEC1_PARTB" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "NO_OF_HOLDERS" NUMBER(10,2), "SHARES_HELD" NUMBER(10,2), "SHARES_IN_TOTAL" NUMBER(20,4), "BOOK_VALUE_SH" NUMBER(10,2), "FACE_VALUE_SH" NUMBER(10,2), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table FIMD_ROC_SEC1_PARTC
--------------------------------------------------------

  CREATE TABLE "FIMD_ROC_SEC1_PARTC" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "RESIDENT" NUMBER(20,4), "NON_RESIDENT" NUMBER(20,4), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table FIMD_ROC_SEC1_PARTD
--------------------------------------------------------

  CREATE TABLE "FIMD_ROC_SEC1_PARTD" ("SR_NO" NUMBER, "NAME_CONTROLLER" VARCHAR2(100), "NO_OF_SH" NUMBER(10,2), "HOLD_TOTAL_EQUITY" NUMBER(20,4), "RESIDANCE_STATUS" VARCHAR2(100), "NAME_ASSO_SH" VARCHAR2(100), "THEIR_RESIDANCE_STATUS" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_ROC_SEC1_PART_A
--------------------------------------------------------

  CREATE TABLE "FIMD_ROC_SEC1_PART_A" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" NUMBER(10,2), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_ROC_SEC2
--------------------------------------------------------

  CREATE TABLE "FIMD_ROC_SEC2" ("SR_NO" NUMBER, "NAME_DIRECTOR" VARCHAR2(100), "OCCUPATION" VARCHAR2(100), "ADRESS" VARCHAR2(100), "APPOINTMENT_BOARD" VARCHAR2(100), "BOARD_COMMITEE" VARCHAR2(100), "OTHER_COMP_DIR_HELD" VARCHAR2(100), "NATURE_INTRST_OTHER" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_ROC_SEC2_PARTB
--------------------------------------------------------

  CREATE TABLE "FIMD_ROC_SEC2_PARTB" ("SR_NO" NUMBER, "NAME_DIRECTOR" VARCHAR2(100), "OCCUPATION" VARCHAR2(100), "ADRESS" VARCHAR2(100), "APPOINTMENT_BOARD" VARCHAR2(100), "BOARD_COMMITEE" VARCHAR2(100), "OTHER_COMP_DIR_HELD" VARCHAR2(100), "NATURE_INTRST_OTHER" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_ROC_SEC2_PARTC
--------------------------------------------------------

  CREATE TABLE "FIMD_ROC_SEC2_PARTC" ("SR_NO" NUMBER, "EXECUTIVE" VARCHAR2(100), "NAME" VARCHAR2(100), "DESIGNATION" VARCHAR2(100), "APOINTED_SINCE_FI" VARCHAR2(100), "APOINTED_INCUBLET_POS" VARCHAR2(100), "LOCATED_AT" VARCHAR2(100), "TELEPHONE_NO" NUMBER, "FAX_NO" NUMBER, "EMAIL_ID" VARCHAR2(100), "TRANSC_ID" VARCHAR2(100), "RDATE" DATE, "CODE" NUMBER);

--------------------------------------------------------
--  DDL for Table FIMD_ROC_SEC3
--------------------------------------------------------

  CREATE TABLE "FIMD_ROC_SEC3" ("SR_NO" NUMBER, "NAME_AUDITOR" VARCHAR2(100), "ADRESS_AUDITOR" VARCHAR2(100), "DT_APOINT_AUDITOR_FI" VARCHAR2(100), "DT_TENTURE_AUDITOR_END" VARCHAR2(100), "TRANSC_ID" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_ROC_SIGN
--------------------------------------------------------

  CREATE TABLE "FIMD_ROC_SIGN" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_ROQ_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "FIMD_ROQ_GEN_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_ROR_Q_GEN_INFO
--------------------------------------------------------

  CREATE TABLE "FIMD_ROR_Q_GEN_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_ROR_Q_SEC_A
--------------------------------------------------------

  CREATE TABLE "FIMD_ROR_Q_SEC_A" ("SR_NO" NUMBER, "LINE_ITEM" VARCHAR2(500), "DOM_OP_CQ" NUMBER, "DOM_OP_CY" NUMBER, "OVER_OP_CQ" NUMBER, "OVER_OP_CY" NUMBER, "GLB_OP_CQ" NUMBER, "GLB_OP_CY" NUMBER, "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_ROR_Q_SEC_A_NO_OF_STAFF
--------------------------------------------------------

  CREATE TABLE "FIMD_ROR_Q_SEC_A_NO_OF_STAFF" ("SR_NO" NUMBER, "LINE_ITEM" VARCHAR2(500), "DOM" NUMBER, "OVER" NUMBER, "GLB" NUMBER, "CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_ROR_Q_SEC_B
--------------------------------------------------------

  CREATE TABLE "FIMD_ROR_Q_SEC_B" ("SR_NO" NUMBER, "LINE_ITEM" VARCHAR2(500), "DOM_OP" NUMBER, "OVER_OP" NUMBER, "GLB_OP" NUMBER, "CODE" NUMBER, "TYP_ID" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table FIMD_ROR_Q_SIGN
--------------------------------------------------------

  CREATE TABLE "FIMD_ROR_Q_SIGN" ("SR_NO" NUMBER, "AUTHORIZED_REPORTING_OFFICIAL" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" VARCHAR2(100), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table GROUP_MASTER_CIMS
--------------------------------------------------------

  CREATE TABLE "GROUP_MASTER_CIMS" ("CODE" VARCHAR2(250), "NAME" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table GROUP_MASTER_CIMS_BKUP
--------------------------------------------------------

  CREATE TABLE "GROUP_MASTER_CIMS_BKUP" ("CODE" VARCHAR2(250), "NAME" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table IDEALCONTROLTABLE
--------------------------------------------------------

  CREATE TABLE "IDEALCONTROLTABLE" ("SR_NO" NUMBER, "REPORT_NAME" VARCHAR2(100), "FREQUENCY" VARCHAR2(50), "RETURN_CODE" VARCHAR2(11), "RECORD_STATUS" VARCHAR2(20), "GAP" VARCHAR2(20), "REPORTING_DATE" DATE, "VALIDATION_FILE" VARCHAR2(100), "RENDER_FILE" VARCHAR2(100), "FILE_NAME" VARCHAR2(100), "CREATED_BY" VARCHAR2(50), "GAP_FILE" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table IDEALCONTROLTABLE3
--------------------------------------------------------

  CREATE TABLE "IDEALCONTROLTABLE3" ("SR_NO" NUMBER, "REPORT_NAME" VARCHAR2(100), "FREQUENCY" VARCHAR2(50), "RETURN_CODE" VARCHAR2(11), "RECORD_STATUS" VARCHAR2(20), "GAP" VARCHAR2(20), "REPORTING_DATE" DATE, "VALIDATION_FILE" VARCHAR2(100), "RENDER_FILE" VARCHAR2(100), "XBRL_FILE" VARCHAR2(100), "GAP_FILE" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table IDEALCONTROLTABLE5
--------------------------------------------------------

  CREATE TABLE "IDEALCONTROLTABLE5" ("SR_NO" NUMBER, "REPORT_NAME" VARCHAR2(100), "FREQUENCY" VARCHAR2(50), "RETURN_CODE" VARCHAR2(11), "RECORD_STATUS" VARCHAR2(20), "GAP" VARCHAR2(20), "REPORTING_DATE" DATE, "VALIDATION_FILE" VARCHAR2(100), "RENDER_FILE" VARCHAR2(100), "FILE_NAME" VARCHAR2(100), "CREATED_BY" VARCHAR2(50), "GAP_FILE" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table IDEAL_CRILC_SECTION_1_ORG
--------------------------------------------------------

  CREATE TABLE "IDEAL_CRILC_SECTION_1_ORG" ("RPT_SR_NO" NUMBER, "PAN" VARCHAR2(250), "CUSTOMER_NAME" VARCHAR2(1000), "LEI" VARCHAR2(250), "CIN" VARCHAR2(250), "BORROWER_GROUP_CODE" VARCHAR2(250), "BORROWER_GROUP_NAME" VARCHAR2(1000), "INDUSTRY_CODE" VARCHAR2(1000), "INDUSTRY_NAME" VARCHAR2(1000), "SECTOR_CODE" VARCHAR2(1000), "BANKING_ARRANGEMENT" VARCHAR2(1000), "LEAD_BANK_NAME" VARCHAR2(1000), "INTERNAL_RATING" VARCHAR2(1000), "EXTERNAL_RATING" VARCHAR2(1000), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "DATE_NPA_CLASSIFY" VARCHAR2(100), "RESTRUCTING_SCHEME_DATE" VARCHAR2(100), "BRWR_CLASIFID_FRAUD_DEFAULT" VARCHAR2(1000), "DATE_CLASS_WILF_DEFAULT" VARCHAR2(100), "WH_CLASS_RFA_FRAUD" VARCHAR2(1000), "DATE_CLASS_RFA_FRAUD" VARCHAR2(100), "NPA_DUE_FOREIGN_COUNTRY" VARCHAR2(20), "SPECIAL_MENTION_ACCOUNTS" VARCHAR2(1000), "DATE_SMA_CLASSIFY" VARCHAR2(100), "RESOLUTION_PLAN_STATUS" VARCHAR2(250), "DATE_FILING_WITH_NCLT" VARCHAR2(250), "DATE_ADDMISSION" VARCHAR2(250), "LOAN_BUYOUT_TAKEOVER" VARCHAR2(200), "DATE_BUYOUT_TAKEOVER" VARCHAR2(200), "WHETHER_CC_OD_FAC" VARCHAR2(200), "AGGREGATE_FUND_BASED_WC_LIMIT" VARCHAR2(200), "OF_WHICH_INTRA_CR_LIMIT" VARCHAR2(200), "LIMIT_SANCTIONED_FUNDED" VARCHAR2(250), "CASH_CREDIT_OVERDRAFT" VARCHAR2(250), "WORKING_CAPITAL_DEMAND_LOAN" VARCHAR2(250), "INLAND_BILLS" VARCHAR2(250), "PACKING_CREDIT" VARCHAR2(250), "EXPORT_BILLS" VARCHAR2(250), "TERM_LOAN" VARCHAR2(250), "BILLS_DISCONTINUED_DEFRED" VARCHAR2(250), "OTHER_FUNDED_OUTSTANDING" VARCHAR2(250), "TOTAL_FUNDED_OUTSTANDING" VARCHAR2(250), "AMT_ELIGIBLE_NETNG_FUNDEDEXPO" VARCHAR2(250), "FUNDED_CREDIT_EXPOSURE" VARCHAR2(250), "SECURED_FUNDED_AMT" VARCHAR2(200), "LIMIT_SANCTIONED_NON_FUNDED" VARCHAR2(250), "LETTER_OF_CREDIT" VARCHAR2(250), "GUARANTEES" VARCHAR2(250), "ACCEPTANCES" VARCHAR2(250), "FOREIGN_EXCHANGE_CONTRACTS" VARCHAR2(250), "INTEREST_RATE_DERIVATIVES" VARCHAR2(250), "OTHER_NONFUNDED_OUTSTANDING" VARCHAR2(250), "TOTAL_NONFUNDED_OUTSTANDING" VARCHAR2(250), "AMT_ELIGIBLE_NETNG_NONFUNDED" VARCHAR2(250), "NONFUNDED_CREDIT_EXPOSURE" VARCHAR2(250), "TOTAL_LMT_SANCTIONED_BRWR" VARCHAR2(250), "TOTAL_AMT_OUTSTANDING" VARCHAR2(250), "OF_WHICH_ADD_FIN_CLASIFY" VARCHAR2(100), "TOTAL_CREDIT_EXPOSURE" VARCHAR2(250), "TOTAL_CREDIT_EXPO_CRM" VARCHAR2(250), "TCE_AS_PRCNT_OF_CAPITAL_FUNDS" VARCHAR2(250), "TOTAL_INVESTMENT_EXPOSURE" VARCHAR2(250), "TOTAL_EXPOSURE" VARCHAR2(250), "OFTE_FOREIGN_CURRENCY_EXPOSURE" VARCHAR2(250), "TOTAL_EXPOSURE_CRM" VARCHAR2(250), "TE_AS_PRCNT_OF_CAPITAL_FUNDS" VARCHAR2(250), "EXPO_OVERSEAS_BRNCH_INDIANBANK" VARCHAR2(250), "TOTAL_PROVISIONS_HELD_NPA" VARCHAR2(100), "DICGC_ECGC_CGMTMSE_OTHERCLAIMS" VARCHAR2(250), "UNSECURED_AMT_OUTSTANDING" VARCHAR2(250), "CURRENT_ACCOUNT_BALANCE" VARCHAR2(250), "AMT_PRUDENTIALLY_WRITTEN_OFF" VARCHAR2(250), "DATE_PRUDENTIALLY_WRITTEN_OFF" VARCHAR2(200), "WO_THROUGH_SETTLE" VARCHAR2(250), "OTHER_WO" VARCHAR2(250), "TOTAL_WO" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table IDEAL_CRILC_SECTION_1_ORG_REPORTINGDATE
--------------------------------------------------------

  CREATE TABLE "IDEAL_CRILC_SECTION_1_ORG_REPORTINGDATE" ("RPT_SR_NO" NUMBER, "PAN" VARCHAR2(250), "CUSTOMER_NAME" VARCHAR2(1000), "LEI" VARCHAR2(250), "CIN" VARCHAR2(250), "BORROWER_GROUP_CODE" VARCHAR2(250), "BORROWER_GROUP_NAME" VARCHAR2(1000), "INDUSTRY_CODE" VARCHAR2(1000), "INDUSTRY_NAME" VARCHAR2(1000), "SECTOR_CODE" VARCHAR2(1000), "BANKING_ARRANGEMENT" VARCHAR2(1000), "LEAD_BANK_NAME" VARCHAR2(1000), "INTERNAL_RATING" VARCHAR2(1000), "EXTERNAL_RATING" VARCHAR2(1000), "ASSETS_CLASSIFICATION" VARCHAR2(1000), "DATE_NPA_CLASSIFY" VARCHAR2(100), "RESTRUCTING_SCHEME_DATE" VARCHAR2(100), "BRWR_CLASIFID_FRAUD_DEFAULT" VARCHAR2(1000), "DATE_CLASS_WILF_DEFAULT" VARCHAR2(100), "WH_CLASS_RFA_FRAUD" VARCHAR2(1000), "DATE_CLASS_RFA_FRAUD" VARCHAR2(100), "NPA_DUE_FOREIGN_COUNTRY" VARCHAR2(20), "SPECIAL_MENTION_ACCOUNTS" VARCHAR2(1000), "DATE_SMA_CLASSIFY" VARCHAR2(100), "RESOLUTION_PLAN_STATUS" VARCHAR2(250), "DATE_FILING_WITH_NCLT" VARCHAR2(250), "DATE_ADDMISSION" VARCHAR2(250), "LOAN_BUYOUT_TAKEOVER" VARCHAR2(200), "DATE_BUYOUT_TAKEOVER" VARCHAR2(200), "WHETHER_CC_OD_FAC" VARCHAR2(200), "AGGREGATE_FUND_BASED_WC_LIMIT" VARCHAR2(200), "OF_WHICH_INTRA_CR_LIMIT" VARCHAR2(200), "LIMIT_SANCTIONED_FUNDED" VARCHAR2(250), "CASH_CREDIT_OVERDRAFT" VARCHAR2(250), "WORKING_CAPITAL_DEMAND_LOAN" VARCHAR2(250), "INLAND_BILLS" VARCHAR2(250), "PACKING_CREDIT" VARCHAR2(250), "EXPORT_BILLS" VARCHAR2(250), "TERM_LOAN" VARCHAR2(250), "BILLS_DISCONTINUED_DEFRED" VARCHAR2(250), "OTHER_FUNDED_OUTSTANDING" VARCHAR2(250), "TOTAL_FUNDED_OUTSTANDING" VARCHAR2(250), "AMT_ELIGIBLE_NETNG_FUNDEDEXPO" VARCHAR2(250), "FUNDED_CREDIT_EXPOSURE" VARCHAR2(250), "SECURED_FUNDED_AMT" VARCHAR2(200), "LIMIT_SANCTIONED_NON_FUNDED" VARCHAR2(250), "LETTER_OF_CREDIT" VARCHAR2(250), "GUARANTEES" VARCHAR2(250), "ACCEPTANCES" VARCHAR2(250), "FOREIGN_EXCHANGE_CONTRACTS" VARCHAR2(250), "INTEREST_RATE_DERIVATIVES" VARCHAR2(250), "OTHER_NONFUNDED_OUTSTANDING" VARCHAR2(250), "TOTAL_NONFUNDED_OUTSTANDING" VARCHAR2(250), "AMT_ELIGIBLE_NETNG_NONFUNDED" VARCHAR2(250), "NONFUNDED_CREDIT_EXPOSURE" VARCHAR2(250), "TOTAL_LMT_SANCTIONED_BRWR" VARCHAR2(250), "TOTAL_AMT_OUTSTANDING" VARCHAR2(250), "OF_WHICH_ADD_FIN_CLASIFY" VARCHAR2(100), "TOTAL_CREDIT_EXPOSURE" VARCHAR2(250), "TOTAL_CREDIT_EXPO_CRM" VARCHAR2(250), "TCE_AS_PRCNT_OF_CAPITAL_FUNDS" VARCHAR2(250), "TOTAL_INVESTMENT_EXPOSURE" VARCHAR2(250), "TOTAL_EXPOSURE" VARCHAR2(250), "OFTE_FOREIGN_CURRENCY_EXPOSURE" VARCHAR2(250), "TOTAL_EXPOSURE_CRM" VARCHAR2(250), "TE_AS_PRCNT_OF_CAPITAL_FUNDS" VARCHAR2(250), "EXPO_OVERSEAS_BRNCH_INDIANBANK" VARCHAR2(250), "TOTAL_PROVISIONS_HELD_NPA" VARCHAR2(100), "DICGC_ECGC_CGMTMSE_OTHERCLAIMS" VARCHAR2(250), "UNSECURED_AMT_OUTSTANDING" VARCHAR2(250), "CURRENT_ACCOUNT_BALANCE" VARCHAR2(250), "AMT_PRUDENTIALLY_WRITTEN_OFF" VARCHAR2(250), "DATE_PRUDENTIALLY_WRITTEN_OFF" VARCHAR2(200), "WO_THROUGH_SETTLE" VARCHAR2(250), "OTHER_WO" VARCHAR2(250), "TOTAL_WO" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table IDEAL_CRILC_SECTION_2_ORG
--------------------------------------------------------

  CREATE TABLE "IDEAL_CRILC_SECTION_2_ORG" ("RPT_SR_NO" VARCHAR2(100), "PAN" VARCHAR2(250), "BORROWER_CUSTOMER_NAME" VARCHAR2(250), "BORROWER_GROUP_CODE" VARCHAR2(250), "GROUP_NAME" VARCHAR2(250), "INDUSTRY_CODE" VARCHAR2(250), "INDUSTRY_NAME" VARCHAR2(250), "BWR_CLSFID_WILFUL" VARCHAR2(100), "DATE_CLASS_WILF_DEFAULT" VARCHAR2(100), "WH_CLASS_RFA_FRAUD" VARCHAR2(1000), "DATE_CLASS_RFA_FRAUD" VARCHAR2(100), "AMOUNT_TECHNI_PRU_WRITOFF" VARCHAR2(250), "DATEWHEN_PRU_TECHNI_WRITTOFF" VARCHAR2(250), "WO_THROUGH_SETTLE" VARCHAR2(250), "OTHER_WO" VARCHAR2(250), "TOTAL_WO" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table IDEAL_CRILC_SECTION_2_ORG_REPORTINGDATE
--------------------------------------------------------

  CREATE TABLE "IDEAL_CRILC_SECTION_2_ORG_REPORTINGDATE" ("RPT_SR_NO" VARCHAR2(100), "PAN" VARCHAR2(250), "BORROWER_CUSTOMER_NAME" VARCHAR2(250), "BORROWER_GROUP_CODE" VARCHAR2(250), "GROUP_NAME" VARCHAR2(250), "INDUSTRY_CODE" VARCHAR2(250), "INDUSTRY_NAME" VARCHAR2(250), "BWR_CLSFID_WILFUL" VARCHAR2(100), "DATE_CLASS_WILF_DEFAULT" VARCHAR2(100), "WH_CLASS_RFA_FRAUD" VARCHAR2(1000), "DATE_CLASS_RFA_FRAUD" VARCHAR2(100), "AMOUNT_TECHNI_PRU_WRITOFF" VARCHAR2(250), "DATEWHEN_PRU_TECHNI_WRITTOFF" VARCHAR2(250), "WO_THROUGH_SETTLE" VARCHAR2(250), "OTHER_WO" VARCHAR2(250), "TOTAL_WO" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table IDEAL_CRILC_SECTION_3_ORG
--------------------------------------------------------

  CREATE TABLE "IDEAL_CRILC_SECTION_3_ORG" ("RPT_SR_NO" NUMBER, "PAN" VARCHAR2(100), "CUSTOMER_NAME" VARCHAR2(1000), "TOTALCREDITSUMDURREPPER" NUMBER, "TOTALDEBITSUMDURREPPER" NUMBER, "BALANCE_IN_CURRENT_ACCOUNT" VARCHAR2(250), "WHETHER_CC_OD_FAC" VARCHAR2(200), "WHETHER_CURR_AC" VARCHAR2(200), "REPORTING_DATE" VARCHAR2(1000));

--------------------------------------------------------
--  DDL for Table IDEAL_CRILC_SECTION_3_ORG_REPORTINGDATE
--------------------------------------------------------

  CREATE TABLE "IDEAL_CRILC_SECTION_3_ORG_REPORTINGDATE" ("RPT_SR_NO" NUMBER, "PAN" VARCHAR2(100), "CUSTOMER_NAME" VARCHAR2(1000), "TOTALCREDITSUMDURREPPER" NUMBER, "TOTALDEBITSUMDURREPPER" NUMBER, "BALANCE_IN_CURRENT_ACCOUNT" VARCHAR2(250), "WHETHER_CC_OD_FAC" VARCHAR2(200), "WHETHER_CURR_AC" VARCHAR2(200), "REPORTING_DATE" VARCHAR2(1000));

--------------------------------------------------------
--  DDL for Table IDEAL_CRILC_SECTION_4_ORG
--------------------------------------------------------

  CREATE TABLE "IDEAL_CRILC_SECTION_4_ORG" ("RPT_SR_NO" NUMBER, "PAN" VARCHAR2(250), "BORROWER_NAME" VARCHAR2(250), "TOTAL_EXPOSURE" VARCHAR2(250), "TOTAL_AMT_OTSTNDG_FUND_NONFNDD" VARCHAR2(250), "RSNS_FOR_CTGONGSNON_CRTVE_BWER" VARCHAR2(3000), "NME_OF_DTRS_PRTNRS_SLE_PROPTER" VARCHAR2(250), "DIRECTOR_IDENTIFICATION_NUMBER" VARCHAR2(250), "STATUS" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table IDEAL_CRILC_SECTION_4_ORG_REPORTINGDATE
--------------------------------------------------------

  CREATE TABLE "IDEAL_CRILC_SECTION_4_ORG_REPORTINGDATE" ("RPT_SR_NO" NUMBER, "PAN" VARCHAR2(250), "BORROWER_NAME" VARCHAR2(250), "TOTAL_EXPOSURE" VARCHAR2(250), "TOTAL_AMT_OTSTNDG_FUND_NONFNDD" VARCHAR2(250), "RSNS_FOR_CTGONGSNON_CRTVE_BWER" VARCHAR2(3000), "NME_OF_DTRS_PRTNRS_SLE_PROPTER" VARCHAR2(250), "DIRECTOR_IDENTIFICATION_NUMBER" VARCHAR2(250), "STATUS" VARCHAR2(250), "REPORTING_DATE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table INDUSTRY_DETAIL_MASTER_CIMS
--------------------------------------------------------

  CREATE TABLE "INDUSTRY_DETAIL_MASTER_CIMS" ("INDUSTRY_CODE" VARCHAR2(250), "INDUSTRY_NAME" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table INT_VALIDATIONDTL
--------------------------------------------------------

  CREATE TABLE "INT_VALIDATIONDTL" ("SR_NO" NUMBER, "ERROR_EXCEL" VARCHAR2(250), "ERROR_SHEET" VARCHAR2(250), "ERROR_DESC" VARCHAR2(500), "ERROR_COLUMN" VARCHAR2(250), "ERROR_VALUE" VARCHAR2(250), "KEY_FIELD" VARCHAR2(250), "KEY_FIELD_VALUE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table LEAD_BANK_MASTER_CIMS
--------------------------------------------------------

  CREATE TABLE "LEAD_BANK_MASTER_CIMS" ("CODE" VARCHAR2(250), "LEAD_BANK_NAME" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table LONBUYOUTTAKEOVR_STATUS_MASTER_CIMS
--------------------------------------------------------

  CREATE TABLE "LONBUYOUTTAKEOVR_STATUS_MASTER_CIMS" ("LOAN_BUYOUT_TAKEOVER_STATUS" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table MASTERSLASTUPDATEDLOG
--------------------------------------------------------

  CREATE TABLE "MASTERSLASTUPDATEDLOG" ("SRNO" NUMBER, "DESTINATIONTABLE" NVARCHAR2(256), "LASTUPDATEDBY" NVARCHAR2(256), "LASTUPDATEDDATETIME" TIMESTAMP(6));

--------------------------------------------------------
--  DDL for Table MEMMASTER
--------------------------------------------------------

  CREATE TABLE "MEMMASTER" ("CODE" NUMBER(10), "DSCR" VARCHAR2(300), "HFLG" VARCHAR2(1), "XBRL_SLNO" NUMBER(38));

--------------------------------------------------------
--  DDL for Table MY_TABLE
--------------------------------------------------------

  CREATE TABLE "MY_TABLE" ("ID" NUMBER, "LARGE_TEXT" CLOB);

--------------------------------------------------------
--  DDL for Table NILL_RPT
--------------------------------------------------------

  CREATE TABLE "NILL_RPT" ("CODE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table NPADueToForeignCountryRegulationMaster
--------------------------------------------------------

  CREATE TABLE "NPADueToForeignCountryRegulationMaster" ("NPADue_ForeignCountry" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table NRB01_D_TABLE1
--------------------------------------------------------

  CREATE TABLE "NRB01_D_TABLE1" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(500), "LOCAL_CURRENCY_X1" VARCHAR2(500), "FOREIGN_CURRENCY_X2" VARCHAR2(500), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB01_D_TABLE2
--------------------------------------------------------

  CREATE TABLE "NRB01_D_TABLE2" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(500), "AMOUNT_X3" VARCHAR2(500), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB01_TABLE1
--------------------------------------------------------

  CREATE TABLE "NRB01_TABLE1" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(500), "LOCAL_CURRENCY_X1" VARCHAR2(500), "FOREIGN_CURRENCY_X2" VARCHAR2(500), "CODE" VARCHAR2(20), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB01_TABLE2
--------------------------------------------------------

  CREATE TABLE "NRB01_TABLE2" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(500), "CODE" VARCHAR2(20), "AMOUNT_X3" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB01_TABLE3
--------------------------------------------------------

  CREATE TABLE "NRB01_TABLE3" ("SRNO" NUMBER, "DESCRIPTION" VARCHAR2(500), "CODE" VARCHAR2(20), "AMOUNT_X4" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB02_LAYOUT1
--------------------------------------------------------

  CREATE TABLE "NRB02_LAYOUT1" ("SR_NO" NUMBER, "COUNTERPARTY_BFI_CODE" VARCHAR2(30), "CURRENT_DEAL_NUMBER" NUMBER, "CURRENCY" VARCHAR2(50), "TYPE_OF_TRANSACTION" VARCHAR2(50), "COUNTERPARTY_BFI_NAME_X1" VARCHAR2(200), "MATURITY_DATE_X2" VARCHAR2(30), "AMOUNT_X3" NUMBER(20,2), "INTEREST_RATE_X4" NUMBER(20,4), "ROLL_OVER_AFTER_MATURITY_X5" VARCHAR2(20), "IF_YES_PREVIOUS_DEAL_NO_X6" VARCHAR2(30), "REMARKS_X7" VARCHAR2(2000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB03_LAYOUT1
--------------------------------------------------------

  CREATE TABLE "NRB03_LAYOUT1" ("SERIAL_NO" NUMBER, "BRANCH_CODE" VARCHAR2(500), "CUSTOMER_CODE" VARCHAR2(500), "CURRENCY" VARCHAR2(500), "SOL_GROUP_CODE_X1" VARCHAR2(500), "SOL_GROUP_NAME_X2" VARCHAR2(500), "ACCOUNT_NUMBER_X3" VARCHAR2(500), "DISBURSEMENT_DATE_X4" VARCHAR2(500), "MATURITY_DATE_X5" VARCHAR2(500), "ADDRESS_BORR_LOC_AUTH_NAME_X6" VARCHAR2(500), "ADDRESS_PRO_LOC_AUTH_NAME_X7" VARCHAR2(500), "INSTIT_GROUPING_OF_BORROWER_X8" VARCHAR2(500), "RESIDENTIAL_STATUS_X9" VARCHAR2(500), "DEPRIVED_SECTOR_X10" VARCHAR2(500), "INDUSTRY_CLASSIFICATION_X11" VARCHAR2(500), "TYPE_OF_LOAN_X12" VARCHAR2(500), "ECONOMIC_SECTOR_X13" VARCHAR2(500), "COLLATERAL_TYPE_X14" VARCHAR2(500), "PAN_X15" VARCHAR2(500), "NATIONAL_ID_CITIZENSHIP_NO_X16" VARCHAR2(500), "CUSTOMER_NAME_X17" VARCHAR2(500), "BANKS_PRODUCT_NAME_X18" VARCHAR2(500), "APPROVED_LIMIT_X19" NUMBER(20,2), "OUTSTANDING_PRINCIPAL_X20" NUMBER(20,2), "OUT_PRIN_AT_AMORTIZED_COST_X21" NUMBER(20,2), "OUTSTAND_PRINCIPAL_FVTPL_X22" NUMBER(20,2), "UNUTILIZED_LIMIT_X23" NUMBER(20,2), "OVERDUE_PRINCIPAL_X24" NUMBER(20,2), "SIMPLE_ACCRUED_INTEREST_X25" NUMBER(20,2), "OTHER_ACCR_INT_INCL_PENAL_X26" NUMBER(20,2), "OVERDUE_INTEREST_X27" NUMBER(20,2), "INTEREST_RATE_X28" NUMBER(20,4), "REPAYMENT_DATE_X29" VARCHAR2(500), "INSURED_UNINSURED_X30" VARCHAR2(500), "LLP_CLASSIFICATION_CODE_X31" VARCHAR2(500), "REQUIRED_PROVISION_X32" NUMBER(20,4), "REQUIRED_PROVISION_AMOUNT_X33" NUMBER(20,2), "ADDITIONAL_PROVISION_X34" NUMBER(20,2), "REASON_FOR_ADDITIONAL_PRO_X35" VARCHAR2(500), "RISK_WGH_TYPE_UNIFIED_DIR_X36" VARCHAR2(500), "RISK_WEIGHT_X37" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB04_LAYOUT1
--------------------------------------------------------

  CREATE TABLE "NRB04_LAYOUT1" ("SERIAL_NO" NUMBER, "NAME_OF_ISSUING_INSTITUTION" VARCHAR2(500), "NAME_OF_COUNTRY" VARCHAR2(500), "INVESTMENT_DATE" VARCHAR2(500), "CURRENCY" VARCHAR2(500), "TYPE_OF_INSTRUMENT" VARCHAR2(500), "NAME_OF_INSTRUMENT_X1" VARCHAR2(500), "CLASSIFICATION_X2" VARCHAR2(500), "NO_OF_UNITS_X3" NUMBER(20,2), "TOTAL_COST_PRICE_X4" NUMBER(20,2), "AMORTIZED_COST_BOOK_VALUE_X5" NUMBER(20,2), "ACCRUED_INTEREST_RECEIVABLE_X6" NUMBER(20,2), "CURRENT_MARKET_PRICE_X7" NUMBER(20,2), "PROVISION_AMOUNT_X8" NUMBER(20,2), "MATURITY_DATE_X9" VARCHAR2(500), "USED_AS_COLLATERAL_X10" VARCHAR2(500), "IF_YES_RELEASE_DATE_X11" VARCHAR2(500), "RISK_WG_TY_AS_PER_UNI_DIR_X12" VARCHAR2(500), "RISK_WEIGHT_X13" NUMBER(20,3), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB04_LAYOUT2
--------------------------------------------------------

  CREATE TABLE "NRB04_LAYOUT2" ("SERIAL_NO" NUMBER, "INVESTMENT_DATE" VARCHAR2(500), "CURRENCY" VARCHAR2(500), "TYPE_OF_INSTRUMENT" VARCHAR2(500), "NAME_OF_INSTRUMENT_X1" VARCHAR2(500), "CLASSIFICATION_X2" VARCHAR2(500), "NO_OF_UNITS_X3" NUMBER(20,2), "TOTAL_COST_PRICE_X4" NUMBER(20,2), "AMORTIZED_COST_BOOK_VALUE_X5" NUMBER(20,2), "ACCRUED_INTEREST_RECEIVABLE_X6" NUMBER(20,2), "CURRENT_MARKET_PRICE_X7" NUMBER(20,2), "PROVISION_AMOUNT_X8" NUMBER(20,2), "MATURITY_DATE_X9" VARCHAR2(500), "USED_AS_COLLATERAL_X10" VARCHAR2(500), "IF_YES_RELEASE_DATE_X11" VARCHAR2(500), "RISK_WEHT_TYPE_UNI_DIR_X12" VARCHAR2(500), "RISK_WEIGHT_X13" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB04_LAYOUT3
--------------------------------------------------------

  CREATE TABLE "NRB04_LAYOUT3" ("SERIAL_NO" NUMBER, "NAME_OF_ISSUING_INSTITUTION" VARCHAR2(500), "NAME_OF_COUNTRY" VARCHAR2(500), "INVESTMENT_DATE" VARCHAR2(500), "CURRENCY" VARCHAR2(500), "TYPE_OF_INSTRUMENT" VARCHAR2(500), "NAME_OF_INSTRUMENT_X1" VARCHAR2(500), "CLASSIFICATION_X2" VARCHAR2(500), "TYPE_OF_INSTITUTION_X3" VARCHAR2(500), "PAID_UP_CAPITAL_THE_COMPANY_X4" NUMBER(20,2), "PAYMENT_STATUS_X5" NUMBER(20,4), "NO_OF_UNITS_X6" NUMBER(20,2), "FACE_VALUE_PER_UNIT_X7" NUMBER(20,2), "COST_PRICE_X8" NUMBER(20,2), "AMORTIZED_COST_BOOK_VALUE_X9" NUMBER(20,2), "ACCRUED_INT_RECEIVABLE_X10" NUMBER(20,2), "CURRENT_MARKET_PRICE_X11" NUMBER(20,2), "PROVISION_AMOUNT_X12" NUMBER(20,2), "INV_ADJ_RESERVE_AMOUNT_X13" NUMBER(20,2), "MATURITY_DATE_X14" VARCHAR2(500), "USED_AS_COLLATERAL_X15" VARCHAR2(500), "IF_YES_RELEASE_DATE_X16" VARCHAR2(500), "RISK_WEIGHT_UNI_DIRECTIVE_X17" VARCHAR2(500), "RISK_WEIGHT_X18" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB04_LAYOUT4
--------------------------------------------------------

  CREATE TABLE "NRB04_LAYOUT4" ("SERIAL_NO" NUMBER, "NAME_OF_ISSUING_INSTITUTION" VARCHAR2(500), "INVESTMENT_DATE" VARCHAR2(500), "CURRENCY" VARCHAR2(500), "TYPE_OF_INVESTMENT" VARCHAR2(500), "TYPE_OF_SHARES" VARCHAR2(500), "CLASSIFICATION_X1" VARCHAR2(500), "RES_STATUS_ISSUE_ENTITY_X2" VARCHAR2(500), "TYPE_OF_INSTITUTION_X3" VARCHAR2(500), "PAID_UP_CAPITAL_OF_COM_X4" NUMBER(20,2), "DEPRIVED_SECTOR_LENDING_X5" VARCHAR2(500), "PAYMENT_STATUS_X6" NUMBER(20,4), "NO_OF_UNITS_X7" NUMBER(20,2), "FACE_VALUE_PER_UNIT_X8" NUMBER(20,2), "COST_PRICE_X9" NUMBER(20,2), "AMORTIZED_COST_BOOK_VALUE_X10" NUMBER(20,2), "ACCRUED_INT_RECEIVABLE_X11" NUMBER(20,2), "CURRENT_MARKET_PRICE_X12" NUMBER(20,2), "PROVISION_AMOUNT_X13" NUMBER(20,2), "INVESTMENT_ADJ_RES_AMT_X14" NUMBER(20,2), "MATURITY_DATE_X15" VARCHAR2(500), "USED_AS_COLLATERAL_X16" VARCHAR2(500), "IF_YES_RELEASE_DATE_X17" VARCHAR2(500), "RISK_WEIGHT_TYPE_UNI_DIR_X18" VARCHAR2(500), "RISK_WEIGHT_X19" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB04_LAYOUT5
--------------------------------------------------------

  CREATE TABLE "NRB04_LAYOUT5" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "CODE" VARCHAR2(500), "PLED_NEPAL_RBIR_TRANSACTION_X1" NUMBER(20,2), "PLED_NEPAL_RBIO_TRANSACTION_X2" NUMBER(20,2), "PLED_OTHER_DOM_CNT_AGA_BOR_X3" NUMBER(20,2), "PLED_OTHER_FORE_CNT_AGA_BOR_X4" NUMBER(20,2), "PLED_OTHER_DOM_CNT_DERI_TRX_X5" NUMBER(20,2), "PLED_OTH_FORE_CNT_DERI_TRX_X6" NUMBER(20,2), "PLED_OTH_CNT_AGA_CON_LI_COM_X7" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB04_LAYOUT6
--------------------------------------------------------

  CREATE TABLE "NRB04_LAYOUT6" ("SR_NO" NUMBER, "BFIS_CODE" VARCHAR2(500), "BFIS_NAME_X1" VARCHAR2(500), "INTERBANK_LENDING_X2" NUMBER(20,2), "OTHER_PLACEMENTS_X3" NUMBER(20,2), "TOTAL_X4" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB05_LAYOUT1
--------------------------------------------------------

  CREATE TABLE "NRB05_LAYOUT1" ("SERIAL_NO" NUMBER, "BRANCH_CODE" VARCHAR2(500), "CURRENCY" VARCHAR2(500), "CLASSIFICATION_OF_DEPOSITORS" VARCHAR2(500), "CATEGORY_OF_DEPOSIT_DIR_16" VARCHAR2(500), "TYPE_OF_ACCOUNT" VARCHAR2(500), "BRANCH_NAME_X1" VARCHAR2(500), "RESIDENTIAL_STATUS_X2" VARCHAR2(500), "CURRENT_STATUS_X3" VARCHAR2(500), "NO_OF_ACCOUNTS_X4" NUMBER(20,2), "AMOUNT_X5" NUMBER(20,2), "ACCRUED_INTEREST_PAYABLE_X6" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB05_LAYOUT2
--------------------------------------------------------

  CREATE TABLE "NRB05_LAYOUT2" ("SERIAL_NO" NUMBER, "BRANCH_CODE" VARCHAR2(500), "BLB_CODE" VARCHAR2(500), "BRANCH_NAME_X1" VARCHAR2(500), "LOCAL_AUTHORITY_NAME_X2" VARCHAR2(500), "LAST_TRX_DATE_DONE_BY_BLB_X3" VARCHAR2(500), "STATUS_OF_DEPOSIT_ACCOUNT_X4" VARCHAR2(500), "TYPE_OF_DEPOSITOR_X5" VARCHAR2(500), "NUMBER_OF_ACCOUNTS_OPENED_X6" NUMBER(20,2), "AMOUNT_X7" NUMBER(20,2), "STATUS_OF_CARDS_ISSUED_X8" VARCHAR2(500), "NUMBER_OF_CARDS_ISSUED_X9" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB05_LAYOUT3A
--------------------------------------------------------

  CREATE TABLE "NRB05_LAYOUT3A" ("SR_NO" NUMBER, "ALL_DEPOSIT_ACCOUNTS_IN_NPR" VARCHAR2(500), "CODE" VARCHAR2(30), "NUMBER_OF_CUSTOMERS_X1" NUMBER(20,2), "AMOUNT_NPR_X2" NUMBER(20,2), "NUMBER_OF_CUSTOMERS_X3" NUMBER(20,2), "AMOUNT_NPR_X4" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB05_LAYOUT3B
--------------------------------------------------------

  CREATE TABLE "NRB05_LAYOUT3B" ("SR_NO" NUMBER, "AGE_GROUP" VARCHAR2(500), "NUMBER_OF_CUSTOMERS_X5" NUMBER(20,2), "NUMBER_OF_ACCOUNTS_X6" NUMBER(20,2), "TOTAL_LCY_DEPOSIT_X7" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB05_LAYOUT4
--------------------------------------------------------

  CREATE TABLE "NRB05_LAYOUT4" ("SR_NO" NUMBER, "DEPOSITS" VARCHAR2(500), "CODE" VARCHAR2(20), "INTEREST_RATE_FOR_LCY_AMT_X1" NUMBER(20,4), "INTEREST_RATE_FOR_LCY_MIN_X2" NUMBER(20,4), "INTEREST_RATE_FOR_LCY_MAX_X3" NUMBER(20,4), "INTEREST_RATE__LCY_WT_AVG_X4" NUMBER(20,4), "INTEREST_RATE_FOR_FCY_AMT_X5" NUMBER(20,4), "INTEREST_RATE_FOR_FCY_MIN_X6" NUMBER(20,4), "INTEREST_RATE_FOR_FCY_MAX_X7" NUMBER(20,4), "INTEREST_RATE__FCY_WT_AVG_X8" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB05_LAYOUT5
--------------------------------------------------------

  CREATE TABLE "NRB05_LAYOUT5" ("SERIAL_NO" NUMBER, "BRANCH_CODE" VARCHAR2(500), "CATEGORIZATION_OF_CUSTOMERS" VARCHAR2(500), "TYPES_OF_SERVICES" VARCHAR2(500), "BRANCH_NAME_X1" VARCHAR2(500), "STATUS_X2" VARCHAR2(500), "NUMBER_OF_CUSTOMERS_X3" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB05_LAYOUT6A
--------------------------------------------------------

  CREATE TABLE "NRB05_LAYOUT6A" ("SERIAL_NO" NUMBER, "NAME_OF_DEPOSITORS" VARCHAR2(500), "PAN_X1" VARCHAR2(500), "NATIONAL_ID_ITIZENSHIP_NO_X2" VARCHAR2(500), "DEPOSIT_AMOUNT_X3" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB05_LAYOUT6B
--------------------------------------------------------

  CREATE TABLE "NRB05_LAYOUT6B" ("SERIAL_NO" NUMBER, "NAME_OF_DEPOSITORS" VARCHAR2(500), "PAN_X4" VARCHAR2(500), "DEPOSIT_AMOUNT_X5" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB05_LAYOUT7
--------------------------------------------------------

  CREATE TABLE "NRB05_LAYOUT7" ("SR_NO" NUMBER, "RANGE_OF_TRANSACTIONS" VARCHAR2(500), "FORM_OF_TRANSACTION" VARCHAR2(500), "TYPE_OF_INSTRUMENT" VARCHAR2(500), "GEOGRAPHICAL_LOCATION" VARCHAR2(500), "CHANNEL_USED" VARCHAR2(500), "NUMBER_OF_TRANSACTIONS_X1" NUMBER, "AMOUNT_X2" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB07_LAYOUT1
--------------------------------------------------------

  CREATE TABLE "NRB07_LAYOUT1" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "CODE" VARCHAR2(40), "ONE_TO_SEVEN_DAYS_X1" NUMBER(20,4), "EIGHT_TO_THIRTY_DAYS_X2" NUMBER(20,4), "THIRTYONE_TO_NINTY_DAYS_X3" NUMBER(20,4), "NINTYONE_180_DAYS_X4" NUMBER(20,4), "ONEEIGHTYONE_TO_270_DAYS_X5" NUMBER(20,4), "TWOSEVENTYONE_TO_365_DAYS_X6" NUMBER(20,4), "ONE_TO_TWO_YEARS_X7" NUMBER(20,4), "TWO_TO_FIVE_YEARS_X8" NUMBER(20,4), "MORE_THAN_5_YEARS_X9" NUMBER(20,4), "TOTAL_X10" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB07_LAYOUT2
--------------------------------------------------------

  CREATE TABLE "NRB07_LAYOUT2" ("SR_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "CODE" VARCHAR2(30), "ONE_TO_30_DAYS_X1" NUMBER(20,4), "THIRTYONE_TO_60_DAYS_X2" NUMBER(20,4), "SIXTYONE_TO_90_DAYS_X3" NUMBER(20,4), "NINTYONE_TO_180_DAYS_X4" NUMBER(20,4), "ONEEIGHTYONE_TO_270_DAYS_X5" NUMBER(20,4), "TWOSEVENTYONE_TO_365_DAYS_X6" NUMBER(20,4), "OVER_1_YEAR_X7" NUMBER(20,4), "TOTAL_X8" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB08_LAYOUT1A
--------------------------------------------------------

  CREATE TABLE "NRB08_LAYOUT1A" ("SR_NO" NUMBER, "CODE_OF_LENDING_INSTITUTION" VARCHAR2(500), "LAST_BORROWING_DATE" VARCHAR2(500), "NAME_OF_LENDING_INSTITUTION_X1" VARCHAR2(500), "OPENING_BALANCE_X2" NUMBER(20,2), "ADDITION_DURING_THE_QUARTER_X3" NUMBER(20,2), "REPAYMENT_DUR_THE_QUARTER_X4" NUMBER(20,2), "OUTSTANDING_BORROWING_AMT_X5" NUMBER(20,2), "REMARKS_X6" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB08_LAYOUT1B
--------------------------------------------------------

  CREATE TABLE "NRB08_LAYOUT1B" ("SR_NO" NUMBER, "NAME_OF_LENDING_INSTITUTION" VARCHAR2(500), "LAST_BORROWING_DATE" VARCHAR2(500), "OPENING_BALANCE_X7" NUMBER(20,2), "ADDITION_DURING_THE_QUARTER_X8" NUMBER(20,2), "REPAYMENT_DUR_THE_QUARTER_X9" NUMBER(20,2), "OUTSTANDING_BORROWING_AMT_X10" NUMBER(20,2), "REMARKS_X11" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB09_LAYOUT1
--------------------------------------------------------

  CREATE TABLE "NRB09_LAYOUT1" ("SERIAL_NO" NUMBER, "ACCOUNT_NUMBER" VARCHAR2(500), "CUSTOMER_ID" VARCHAR2(500), "BORROWER_NAME_X1" VARCHAR2(500), "ADD_OF_BORR_LOCAL_AUTH_NAME_X2" VARCHAR2(500), "PAN_X3" VARCHAR2(500), "NATIONAL_ID_CITIZENSHIP_NO_X4" VARCHAR2(500), "BOOK_DATE_OF_NON_BANKNG_ASS_X5" VARCHAR2(500), "TOT_OUT_PR_BEF_BOOKNG_NBA_X6" NUMBER(20,2), "TOT_OUT_INT_BEF_BOOKNG_NBA_X7" NUMBER(20,2), "OTHERS_OUTSTANDING_BALANCES_X8" NUMBER(20,2), "TOT_VALUATION_OF_COLLATERAL_X9" NUMBER(20,2), "TOT_AMT_OF_NON_BANKNG_ASS_X10" NUMBER(20,2), "LOSS_PROVISION_AMOUNT_X11" NUMBER(20,2), "PER_OF_LOSS_PROVISION_X12" NUMBER(20,4), "CATEGORY_OF_ASSETS_X13" VARCHAR2(500), "BLACKLIST_NO_X14" VARCHAR2(500), "BLACKLISTED_DATE_X15" VARCHAR2(500), "PV_OF_FUTURE_CASH_VALUES_X16" NUMBER(20,2), "IMPAIRMENT_LOSS_BOOKED_X17" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB09_LAYOUT2
--------------------------------------------------------

  CREATE TABLE "NRB09_LAYOUT2" ("SERIAL_NO" NUMBER, "ACCOUNT_NUMBER" VARCHAR2(500), "CUSTOMER_ID" VARCHAR2(500), "BORROWER_NAME_X1" VARCHAR2(500), "ADD_OF_BORR_LOCAL_AUTH_NAME_X2" VARCHAR2(500), "PAN_X3" VARCHAR2(500), "NATIONAL_ID_CITIZENSHIP_NO_X4" VARCHAR2(500), "BOOK_DATE_OF_NON_BANKNG_ASS_X5" VARCHAR2(500), "TOT_OUT_PR_BEF_BOOKNG_NBA_X6" NUMBER(20,2), "TOT_OUT_INT_BEF_BOOKNG_NBA_X7" NUMBER(20,2), "OTHERS_OUTSTANDING_BALANCES_X8" NUMBER(20,2), "TOT_VALUATION_OF_COLLATERAL_X9" NUMBER(20,2), "TOT_AMT_OF_NON_BANKNG_ASS_X10" NUMBER(20,2), "LOSS_PROVISION_AMOUNT_X11" NUMBER(20,2), "DT_OF_ACPT_NBA_BFI_OWN_PUR_X12" VARCHAR2(40), "BOOKED_AMT_X13" NUMBER(20,2), "CATEGORY_OF_ASSETS_X14" VARCHAR2(500), "BLACKLIST_NO_X15" VARCHAR2(500), "BLACKLISTED_DATE_X16" VARCHAR2(500), "PV_OF_FUTURE_CASH_VALUES_X17" NUMBER(20,2), "IMPAIRMENT_LOSS_BOOKED_X18" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB09_LAYOUT3
--------------------------------------------------------

  CREATE TABLE "NRB09_LAYOUT3" ("SERIAL_NO" NUMBER, "ACCOUNT_NUMBER" VARCHAR2(500), "CUSTOMER_ID" VARCHAR2(500), "DATE_OF_WRITE_OFF" VARCHAR2(500), "BORROWER_NAME_X1" VARCHAR2(500), "OUTSTANDING_PRINCIPAL_X2" NUMBER(20,2), "OUTSTANDING_INTEREST_X3" NUMBER(20,2), "OTHERS_OUTSTANDING_BALANCES_X4" NUMBER(20,2), "PRINCIPAL_WRITTEN_OFF_X5" NUMBER(20,2), "INTEREST_WRITTEN_OFF_X6" NUMBER(20,2), "OTHER_BALANCES_WRITTEN_OFF_X7" NUMBER(20,2), "ANY_LEGAL_ACTION_TAKEN_X8" VARCHAR2(500), "BLACKLIST_NO_X9" VARCHAR2(500), "BLACKLISTED_DATE_X10" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB10_LAYOUT1
--------------------------------------------------------

  CREATE TABLE "NRB10_LAYOUT1" ("SERIAL_NO" NUMBER, "CUSTOMER_ID" VARCHAR2(500), "CUSTOMER_NAME_X1" VARCHAR2(500), "PAN_X2" VARCHAR2(500), "NATIONAL_ID_CITIZENSHIP_NO_X3" VARCHAR2(500), "TOTAL_APPROVED_LIMIT_X4" NUMBER(20,2), "TOTAL_OUTSTANDING_PRINCIPAL_X5" NUMBER(20,2), "PARI_PASSU_CONSORTIUM_X6" VARCHAR2(500), "BFIS_UNDER_PARI_PASSU_CONSO_X7" VARCHAR2(2000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB11_LAYOUT1A
--------------------------------------------------------

  CREATE TABLE "NRB11_LAYOUT1A" ("SERIAL_NO" NUMBER, "CUSTOMER_ID" VARCHAR2(500), "BORROWER_NAME_X1" VARCHAR2(500), "PAN_X2" VARCHAR2(500), "NATIONAL_ID_CITIZENSHIP_NO_X3" VARCHAR2(500), "TOT_FUNDED_EXP_CONSORTIUM_X4" NUMBER(20,2), "TOT_NON_FUNDED_EXP_CONSOR_X5" NUMBER(20,2), "LAST_AUDITED_YEAR_X6" VARCHAR2(500), "AUDITORS_NAME_X7" VARCHAR2(500), "PAID_UP_CAPITAL_X8" NUMBER(20,2), "TURNOVER_X9" NUMBER(20,2), "PROFIT_LOSS_X10" NUMBER(20,2), "TAX_AMOUNT_X11" NUMBER(20,2), "NET_WORTH_X12" NUMBER(20,2), "NAME_OF_EXECUTIVE_HEAD_X13" VARCHAR2(500), "ADDRESS_OF_EXECUTIVE_HEAD_X14" VARCHAR2(500), "DATE_OF_APPOINTMENT_X15" VARCHAR2(500), "CONSORTIUM_MEMBERS_X16" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB11_LAYOUT1B
--------------------------------------------------------

  CREATE TABLE "NRB11_LAYOUT1B" ("SERIAL_NO" NUMBER, "CUSTOMER_ID" VARCHAR2(500), "NAME_OF_SHAREHOLDER" VARCHAR2(500), "TYPE_OF_SHAREHOLDER" VARCHAR2(500), "BORROWER_NAME_X17" VARCHAR2(500), "PAN_X18" VARCHAR2(500), "NATIONAL_ID_CITIZENSHIP_NO_X19" VARCHAR2(500), "MEMBER_OF_BOARD_Y_N_X20" VARCHAR2(500), "ADDRESS_OF_SHAREHOLDER_X21" VARCHAR2(500), "PERCENTAGE_PARTICIPATION_X22" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB12_LAYOUT1
--------------------------------------------------------

  CREATE TABLE "NRB12_LAYOUT1" ("SERIAL_NO" NUMBER, "BRANCH_CODE" VARCHAR2(500), "GENDER" VARCHAR2(500), "AGE_GROUP" VARCHAR2(500), "MANAGEMENT_LEVEL_STAFF_X1" NUMBER, "OFFICER_LEVEL_STAFF_X2" NUMBER, "ASSISTANT_LEVEL_STAFF_X3" NUMBER, "CONTRACT_STAFF_X4" NUMBER, "SECURITY_PERSONNEL_X5" NUMBER, "OTHERS_X6" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB12_LAYOUT2
--------------------------------------------------------

  CREATE TABLE "NRB12_LAYOUT2" ("SERIAL_NO" NUMBER, "PROMOTER_NAME" VARCHAR2(500), "NAME_OF_COUNTRY" VARCHAR2(500), "TYPE_OF_PROMOTER" VARCHAR2(500), "PROPRIETOR_NAME_X1" VARCHAR2(500), "DIRECTOR_NAME_1_X2" VARCHAR2(500), "DIRECTOR_NAME_2_X3" VARCHAR2(500), "DIRECTOR_NAME_3_X4" VARCHAR2(500), "DIRECTOR_NAME_4_X5" VARCHAR2(500), "DIRECTOR_NAME_5_X6" VARCHAR2(500), "DIRECTOR_NAME_6_X7" VARCHAR2(500), "DIRECTOR_NAME_7_X8" VARCHAR2(500), "PAN_X9" VARCHAR2(500), "NATIONAL_ID_CITIZENSHIP_NO_X10" VARCHAR2(500), "FATHER_NAME_X11" VARCHAR2(500), "GRAND_FATHER_NAME_X12" VARCHAR2(500), "SPOUSE_NAME_X13" VARCHAR2(500), "DEP_FAMILY_MEMBERS_SEP_BY_X14" VARCHAR2(500), "LOCAL_AUTHORITY_NAME_X15" VARCHAR2(500), "WARD_NO_X16" VARCHAR2(500), "CONTACT_NUMBER_X17" VARCHAR2(500), "NUMBER_OF_SHARE_X18" NUMBER(20,2), "REMARKS_X19" VARCHAR2(2000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB17_LAYOUT1
--------------------------------------------------------

  CREATE TABLE "NRB17_LAYOUT1" ("SERIAL_NO" NUMBER, "INCIDENT_ID" VARCHAR2(500), "TYPE_OF_INCIDENT_X1" VARCHAR2(2000), "REMARKS_IF_OTHERS_X2" VARCHAR2(500), "DATE_AND_TIME_OF_INCIDENT_X3" VARCHAR2(500), "DT_TIME_THE_INCI_DISCOVER_X4" VARCHAR2(500), "ATTACK_SOURCES_X5" VARCHAR2(500), "PRIMARY_FUN_AFFECTED_SYS_X6" VARCHAR2(500), "OPERATING_SYS_AFFECTED_SYS_X7" VARCHAR2(500), "PATCH_LEVEL_AFFECTED_SYSTEM_X8" VARCHAR2(500), "SEC_SOF_LOADED_AFFECTED_SYS_X9" VARCHAR2(500), "PHYSICAL_LOC_AFFECTED_SYS_X10" VARCHAR2(500), "OUTAGE_OF_CRITICAL_IT_SYS_X11" VARCHAR2(500), "ADDITIONAL_SYSTEM_DETAILS_X12" VARCHAR2(500), "TYPE_OF_AFFECTED_DATA_X13" VARCHAR2(2000), "REMARKS_IF_OTHERS_X14" VARCHAR2(500), "IMPACT_ASSESSMENT_X15" VARCHAR2(2000), "REMARKS_IF_OTHERS_X16" VARCHAR2(500), "AMOUNT_OF_FINANCIAL_LOSSES_X17" NUMBER(20,2), "LEVEL_OF_IMPACT_X18" VARCHAR2(500), "REMARKS_IF_OTHERS_X19" VARCHAR2(500), "ESTIMATED_SYS_AFFECTED_X20" NUMBER, "ESTIMATED_USERS_AFFECTED_X21" NUMBER, "THIRD_PARTIES_AFFECTED_X22" VARCHAR2(500), "OTHER_NOTIFIED_AGENCY_X23" VARCHAR2(2000), "NAME_OF_AGENCY_IF_OTHERS_X24" VARCHAR2(500), "NOTIFIED_DATE_X25" VARCHAR2(500), "ACTION_TAKEN_X26" VARCHAR2(2000), "REMARKS_IF_OTHERS_X27" VARCHAR2(500), "NEW_UPDATED_INCIDENT_X28" VARCHAR2(500), "ROOT_CAUSE_ANALYSIS_X29" VARCHAR2(500), "DATE_TARGET_DT_RESOLUTION_X30" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB26_LAYOUT1A
--------------------------------------------------------

  CREATE TABLE "NRB26_LAYOUT1A" ("SERIAL_NO" NUMBER, "TYPES_OF_SHARES" VARCHAR2(500), "CATEGORY" VARCHAR2(500), "TYPE_AS_PER_CONVERSION" VARCHAR2(500), "TYPE_AS_PER_DIVIDEND" VARCHAR2(500), "TYPE_AS_PER_REDEMPTION" VARCHAR2(500), "TYPE_OF_OWNERSHIP" VARCHAR2(500), "OWNERSHIP_BY" VARCHAR2(500), "MATURITY_DATE_X1" VARCHAR2(500), "NUMBER_OF_SHAREHOLDERS_X2" NUMBER(20,2), "NUMBER_OF_SHARES_X3" NUMBER(20,2), "PERCENTAGE_OF_SHAREHOLDING_X4" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB26_LAYOUT1B
--------------------------------------------------------

  CREATE TABLE "NRB26_LAYOUT1B" ("SERIAL_NO" NUMBER, "NAME_OF_SHAREHOLDERS" VARCHAR2(500), "INDIVIDUAL_INSTITUTION" VARCHAR2(500), "SPOUSE_NAME_X5" VARCHAR2(500), "FATHERS_NAME_X6" VARCHAR2(500), "MOTHERS_NAME_X7" VARCHAR2(500), "GRANDFATHERS_NAME_X8" VARCHAR2(500), "TYPE_OF_SHARES_X9" VARCHAR2(500), "PAN_X10" VARCHAR2(500), "NATIONAL_ID_CITIZENSHIP_NO_X11" VARCHAR2(500), "ADDRESS_X12" VARCHAR2(500), "PAID_UP_AMOUNT_X13" NUMBER(20,2), "PERCENTAGE_OF_SHAREHOLDING_X14" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB26_LAYOUT2
--------------------------------------------------------

  CREATE TABLE "NRB26_LAYOUT2" ("SERIAL_NO" NUMBER, "PROMOTERS_NAME" VARCHAR2(500), "LENDING_BFI" VARCHAR2(500), "PAN_X1" VARCHAR2(500), "NATIONAL_ID_CITIZENSHIP_NO_X2" VARCHAR2(500), "TOTAL_NO_OF_SHARES_HELD_X3" NUMBER(20,2), "PER_OF_PAID_UP_CAPITAL_X4" NUMBER(20,4), "NUMBER_OF_SHARE_PLEDGED_X5" NUMBER(20,2), "LOAN_AMOUNT_X6" NUMBER(20,2), "TYPE_OF_LOAN_X7" VARCHAR2(500), "PER_PLEDGED_SHARE_TOT_SHARE_X8" NUMBER(20,4), "REMARKS_X9" VARCHAR2(2000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB26_LAYOUT3
--------------------------------------------------------

  CREATE TABLE "NRB26_LAYOUT3" ("SERIAL_NO" NUMBER, "TYPES_OF_DEBT_SECURITIES" VARCHAR2(500), "CATEGORY" VARCHAR2(500), "TYPE_AS_PER_REDEMPTION" VARCHAR2(500), "TYPE_AS_PER_INTEREST" VARCHAR2(500), "TYPE_AS_PER_CONVERSION" VARCHAR2(500), "TYPE_OF_OWNERSHIP" VARCHAR2(500), "OWNERSHIP_BY" VARCHAR2(500), "MATURITY_DATE_X1" VARCHAR2(500), "TOTAL_FACE_VALUE_X2" NUMBER(20,2), "MEASUREMENT_TYPE_X3" VARCHAR2(500), "AMOUNT_X4" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB28_LAYOUT1
--------------------------------------------------------

  CREATE TABLE "NRB28_LAYOUT1" ("SERIAL_NO" NUMBER, "BRANCH_CODE" VARCHAR2(500), "CUSTOMER_ID" VARCHAR2(500), "ACCOUNT_NUMBER" VARCHAR2(500), "TYPE_OF_ACCOUNT" VARCHAR2(500), "BRANCH_NAME_X1" VARCHAR2(500), "CUSTOMER_NAME_X2" VARCHAR2(500), "PAN_X3" VARCHAR2(500), "NATIONAL_ID_CITIZENSHIP_NO_X4" VARCHAR2(500), "CONTACT_NUMBER_X5" VARCHAR2(500), "DET_OF_NOMINEE_RELATED_PER_X6" VARCHAR2(500), "ACCOUNT_BALANCE_X7" NUMBER(20,2), "DT_OF_LAST_WITHDRAWAL_TRX_X8" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB28_LAYOUT2
--------------------------------------------------------

  CREATE TABLE "NRB28_LAYOUT2" ("SR_NO" NUMBER, "NAME_OF_SHAREHOLDER" VARCHAR2(500), "PAN_X1" VARCHAR2(500), "NATIONAL_ID_CITIZENSHIP_NO_X2" VARCHAR2(500), "NUMBER_OF_SHARES_X3" NUMBER, "DIVIDEND_AMOUNT_X4" NUMBER(20,2), "FISCAL_YEAR_WHICH_RELATED_X5" VARCHAR2(500), "DATE_DECLARATION_DIVIDEND_X6" VARCHAR2(500), "REASONS_FOR_BEING_UNCLAIMED_X7" VARCHAR2(500), "DOES_SHARE_HOLD_DEP_ACC_Y_N_X8" VARCHAR2(500), "IS_THE_ACCOUNT_ACTIVE_X9" VARCHAR2(500), "IF_DORMAN_DT_LAST_WITH_TRX_X10" VARCHAR2(500), "OTHER_DETAILS_X11" VARCHAR2(500), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB30_LAYOUT1
--------------------------------------------------------

  CREATE TABLE "NRB30_LAYOUT1" ("SERIAL_NO" NUMBER, "BRANCH_CODE" VARCHAR2(500), "NATURE_OF_GRIEVANCE" VARCHAR2(500), "BRANCH_NAME_X1" VARCHAR2(500), "REM_IF_OTH_NATURE_GRIEVANCE_X2" VARCHAR2(500), "OPENING_UNSOLVED_GRIEVANCES_X3" NUMBER(20,2), "NO_GRIEVANCES_LODGED_PERIOD_X4" NUMBER(20,2), "NO_OF_GRIEVANCES_RESOLVED_X5" NUMBER(20,2), "NO_OF_GRIEVANCES_UNRESOLVED_X6" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB31_LAYOUT1
--------------------------------------------------------

  CREATE TABLE "NRB31_LAYOUT1" ("SERIAL_NO" NUMBER, "ACTION" VARCHAR2(500), "DATE_OF_ACTION_TAKEN" VARCHAR2(500), "CUSTOMER_CODE" VARCHAR2(500), "ACCOUNT_NUMBER" VARCHAR2(500), "CUSTOMER_NAME_X1" VARCHAR2(500), "PAN_X2" VARCHAR2(500), "NATIONAL_ID_CITIZENSHIP_NO_X3" VARCHAR2(500), "NRB_NOTICE_DATE_X4_" VARCHAR2(500), "ENFORCEMENT_AGENCY_X5" VARCHAR2(500), "REASONS_X6" VARCHAR2(2000), "ACCOUNT_BALANCE_X7" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB32_LAYOUT1
--------------------------------------------------------

  CREATE TABLE "NRB32_LAYOUT1" ("SERIAL_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "CODE" VARCHAR2(500), "AMOUNT_X1" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB36_LAYOUT1
--------------------------------------------------------

  CREATE TABLE "NRB36_LAYOUT1" ("SERIAL_NO" NUMBER, "BRANCH_CODE" VARCHAR2(500), "ACCOUNT_TYPE" VARCHAR2(500), "CLASS" VARCHAR2(500), "DETAILS" VARCHAR2(2000), "BRANCH_NAME_X1" VARCHAR2(500), "DEBIT_AMOUNT_X2" VARCHAR2(500), "CREDIT_AMOUNT_X3" VARCHAR2(500), "REMARKS_X4" VARCHAR2(2000), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB39_LAYOUT1
--------------------------------------------------------

  CREATE TABLE "NRB39_LAYOUT1" ("SERIAL_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "CODE" VARCHAR2(40), "CLOSING_BALANCE_X1" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB39_LAYOUT2
--------------------------------------------------------

  CREATE TABLE "NRB39_LAYOUT2" ("SERIAL_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "CODE" VARCHAR2(40), "TOTAL_X1" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB39_LAYOUT3
--------------------------------------------------------

  CREATE TABLE "NRB39_LAYOUT3" ("SERIAL_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "CODE" VARCHAR2(500), "GROSS_AMOUNT_X1" NUMBER(20,2), "INTEREST_RECEIVABLES_X2" NUMBER(20,2), "TOTAL_X3" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB39_LAYOUT4
--------------------------------------------------------

  CREATE TABLE "NRB39_LAYOUT4" ("SERIAL_NO" NUMBER, "PARTICULARS" VARCHAR2(500), "CODE" VARCHAR2(20), "VALUES_X1" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table NRB_FILING_INFO
--------------------------------------------------------

  CREATE TABLE "NRB_FILING_INFO" ("SR_NO" NUMBER, "DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(100), "CODE" NUMBER, "RETURN_CODE" NUMBER, "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table ORACLETEST
--------------------------------------------------------

  CREATE TABLE "ORACLETEST" ("LINENUMBER" VARCHAR2(100), "REPORTTYPE" VARCHAR2(100), "REPORTINGDATE" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table PAN_MASTER_CIMS
--------------------------------------------------------

  CREATE TABLE "PAN_MASTER_CIMS" ("PAN_NO" VARCHAR2(20), "NAME" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table PAN_TCE_TE
--------------------------------------------------------

  CREATE TABLE "PAN_TCE_TE" ("PAN" VARCHAR2(20), "TCE_AS_PRCNT_OF_CAPITAL_FUNDS" NUMBER, "TE_AS_PRCNT_OF_CAPITAL_FUNDS" NUMBER);

--------------------------------------------------------
--  DDL for Table PROJECT_CONSTANT
--------------------------------------------------------

  CREATE TABLE "PROJECT_CONSTANT" ("CONSTANT_KEY" VARCHAR2(1020), "VALUE" VARCHAR2(1020));

--------------------------------------------------------
--  DDL for Table QCB_F014_FILING_INFO
--------------------------------------------------------

  CREATE TABLE "QCB_F014_FILING_INFO" ("DESCRIPTION" VARCHAR2(200), "VALUE" VARCHAR2(200), "CODE" VARCHAR2(200), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QCB_F014_FUNDING_GEO
--------------------------------------------------------

  CREATE TABLE "QCB_F014_FUNDING_GEO" ("COUNTRY" VARCHAR2(200), "SOVEREIGNS" NUMBER(20,2), "MULTI_DEV_BANKS" NUMBER(20,2), "PUBLIC_SECTOR_ENT" NUMBER(20,2), "FOR_PROFIT_GOV_RLTD_ENT" NUMBER(20,2), "BANKS" NUMBER(20,2), "PVT_SEC_LARGE_CORP" NUMBER(20,2), "PVT_SEC_SMES" NUMBER(20,2), "NBF_INSTITUTIONS" NUMBER(20,2), "RETAIL" NUMBER(20,2), "TOTAL" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_BR330_CREDIT_RISK_CONC_ADDL_MEMO_ITEMS1_TBL3
--------------------------------------------------------

  CREATE TABLE "QFCRA_BR330_CREDIT_RISK_CONC_ADDL_MEMO_ITEMS1_TBL3" ("DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(10), "NET_EXPOSURE_OUTSTANDING" NUMBER(20,2), "NET_EXPOSURE_PCT_TOTAL_ASSETS" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_BR330_CREDIT_RISK_CONC_ADDL_MEMO_ITEMS2_TBL4
--------------------------------------------------------

  CREATE TABLE "QFCRA_BR330_CREDIT_RISK_CONC_ADDL_MEMO_ITEMS2_TBL4" ("DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(10), "AMOUNT" NUMBER(10,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_BR330_CREDIT_RISK_CONC_LARGE_EQUITY_EXPOS_TBL7
--------------------------------------------------------

  CREATE TABLE "QFCRA_BR330_CREDIT_RISK_CONC_LARGE_EQUITY_EXPOS_TBL7" ("DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(10,2), "LARGE_EXPOSURE_LEI" VARCHAR2(100), "FINANCIAL_INSTITUTION_YN" VARCHAR2(10), "DEDUCTED_FROM_CAPITAL_OR_RWA" VARCHAR2(100), "TOTAL_EQUITY_EXPOSURE" NUMBER(20,2), "PRIVATE_EQUITY_EXPOSURE" NUMBER(20,2), "PUBLIC_EQUITY_EXPOSURE" NUMBER(20,2), "EQUITY_EXPOSURE_PCT_QUAL_CAPITAL" NUMBER(20,4), "ON_BAL_SHEET_EXP_ORIGINATED_CREDIT" NUMBER(20,2), "ON_BAL_SHEET_EXP_DEBT_INSTRUMENTS" NUMBER(20,2), "OFF_BAL_SHEET_EXPOSURE" NUMBER(20,2), "GROSS_CREDIT_EXPOSURE" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_BR330_CREDIT_RISK_CONC_LARGE_EXPOSER_SUM_TBL1
--------------------------------------------------------

  CREATE TABLE "QFCRA_BR330_CREDIT_RISK_CONC_LARGE_EXPOSER_SUM_TBL1" ("DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(10), "ON_BAL_SHEET_EXP_ORIGINATED_CREDIT" NUMBER(20,2), "ON_BAL_SHEET_EXP_DEBT_INSTRUMENTS" NUMBER(20,2), "ON_BAL_SHEET_EXP_EQUITY" NUMBER(20,2), "OFF_BAL_SHEET_EXPOSURE" NUMBER(20,2), "GROSS_EXPOSURE" NUMBER(20,2), "MEMORANDUM_ITEM" NUMBER(20,2), "GROSS_EXPOSURE_PCT_QUAL_CAPITAL" NUMBER(20,4), "SPECIFIC_CREDIT_PROVISION" NUMBER(20,2), "NET_EXPOSURE_AFTER_CRM" NUMBER(20,2), "NET_EXPOSURE_PCT_QUAL_CAPITAL" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_BR330_CREDIT_RISK_CONC_NAME_LARGE_EXPOSER_TBL5
--------------------------------------------------------

  CREATE TABLE "QFCRA_BR330_CREDIT_RISK_CONC_NAME_LARGE_EXPOSER_TBL5" ("DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(10,2), "GROUP_OR_SINGLE_OBLIGOR_LEVEL" VARCHAR2(50), "LEGAL_ENTITY_IDENTIFIER" VARCHAR2(100), "RELATED_PARTY_YN" VARCHAR2(10), "FINANCIAL_INSTITUTION_YN" VARCHAR2(10), "COUNTRY_DOMICILE" VARCHAR2(100), "ON_BAL_SHEET_EXP_ORIGINATED_CREDIT" NUMBER(20,2), "ON_BAL_SHEET_EXP_DEBT_INSTRUMENTS" NUMBER(20,2), "OFF_BAL_SHEET_EXPOSURE" NUMBER(20,2), "GROSS_CREDIT_EXPOSURE" NUMBER(20,2), "SPECIFIC_CREDIT_IMPAIRMENT" NUMBER(20,2), "NET_EXPOSURE_AFTER_CRM" NUMBER(20,2), "NET_EXPOSURE_PCT_QUAL_CAPITAL" NUMBER(20,4), "MAX_UTILISATION_DURING_QUARTER" NUMBER(20,2), "EXCESSES_EXEMPT_BY_QFCRA" NUMBER(20,2), "EXCESSES_GUARANTEED_BY_PARENT" NUMBER(20,2), "TOTAL_EQUITY_EXPOSURE" NUMBER(20,2), "PRIVATE_EQUITY_EXPOSURE" NUMBER(20,2), "PUBLIC_EQUITY_EXPOSURE" NUMBER(20,2), "GROSS_DEBT_EQUITY_EXPOSURE" NUMBER(20,2), "GROSS_EXPOSURE_PCT_QUAL_CAPITAL" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_BR330_CREDIT_RISK_CONC_NAME_LARGE_EXPOSER_TBL6
--------------------------------------------------------

  CREATE TABLE "QFCRA_BR330_CREDIT_RISK_CONC_NAME_LARGE_EXPOSER_TBL6" ("DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(20,2), "PARENT_NAME" VARCHAR2(100), "ULTIMATE_GROUP_LEI" VARCHAR2(100), "LARGE_EXPOSURE_LEI" VARCHAR2(100), "RELATED_PARTY_YN" VARCHAR2(10), "FINANCIAL_INSTITUTION_YN" VARCHAR2(10), "CONNECTION_TYPE" VARCHAR2(100), "ON_BAL_SHEET_EXP_ORIGINATED_CREDIT" NUMBER(20,2), "ON_BAL_SHEET_EXP_DEBT_INSTRUMENTS" NUMBER(20,2), "OFF_BAL_SHEET_EXPOSURE" NUMBER(20,2), "GROSS_CREDIT_EXPOSURE" NUMBER(20,2), "SPECIFIC_CREDIT_IMPAIRMENT" NUMBER(20,2), "NET_EXPOSURE_AFTER_CRM" NUMBER(20,2), "NET_EXPOSURE_PCT_QUAL_CAPITAL" NUMBER(20,4), "MAX_UTILISATION_DURING_QUARTER" NUMBER(20,2), "EXCESSES_EXEMPT_BY_QFCRA" NUMBER(20,2), "EXCESSES_GUARANTEED_BY_PARENT" NUMBER(20,2), "TOTAL_EQUITY_EXPOSURE" NUMBER(20,2), "PRIVATE_EQUITY_EXPOSURE" NUMBER(20,2), "PUBLIC_EQUITY_EXPOSURE" NUMBER(20,2), "GROSS_DEBT_EQUITY_EXPOSURE" NUMBER(20,2), "GROSS_EXPOSURE_PCT_QUAL_CAPITAL" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_BR330_CREDIT_RISK_CONC_RELATED_PARTY_NAME_TBL8
--------------------------------------------------------

  CREATE TABLE "QFCRA_BR330_CREDIT_RISK_CONC_RELATED_PARTY_NAME_TBL8" ("DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(10,2), "RELATED_PARTY_CATEGORY_PRINCIPAL" VARCHAR2(100), "RELATED_PARTY_CATEGORY_CONNECTION" VARCHAR2(100), "RELATED_PARTY_CATEGORY_NATURE_CONN" VARCHAR2(100), "EXPOSURE_APPROVED" NUMBER(20,2), "EXPOSURE_DRAWN_DOWN" NUMBER(20,2), "EXPOSURE_OUTSTANDING" NUMBER(20,2), "EXEMPT_EXPOSURES" NUMBER(20,2), "NET_EXPOSURE_OUTSTANDING" NUMBER(20,2), "CLASSIFIED_EXPOSURE" NUMBER(20,2), "NET_EXPOSURE_PCT_TOTAL_ASSETS" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_BR330_CREDIT_RISK_CONC_TOTAL_TBL2
--------------------------------------------------------

  CREATE TABLE "QFCRA_BR330_CREDIT_RISK_CONC_TOTAL_TBL2" ("DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(10), "TOTAL" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_BR340_CREDIT_RISK_DISTRIBUTION_TBL1
--------------------------------------------------------

  CREATE TABLE "QFCRA_BR340_CREDIT_RISK_DISTRIBUTION_TBL1" ("DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(10), "ON_BAL_SHEET_EXP_ORIGINATED_CREDIT" NUMBER(20,2), "ON_BAL_SHEET_EXP_DEBT_INSTRUMENTS" NUMBER(20,2), "ON_BAL_SHEET_EXP_EQUITY" NUMBER(20,2), "OFF_BAL_SHEET_EXPOSURE" NUMBER(20,2), "GROSS_EXPOSURE" NUMBER(20,2), "MEMORANDUM_ITEM" NUMBER(20,2), "GROSS_EXPOSURE_PCT_QUAL_CAPITAL" NUMBER(20,4), "TOTAL_PROVISIONS" NUMBER(20,2), "SPECIFIC_PROVISIONS" NUMBER(20,2), "PORTFOLIO_GENERAL_PROVISIONS" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_BR340_CREDIT_RISK_DISTRIBUTION_TBL3
--------------------------------------------------------

  CREATE TABLE "QFCRA_BR340_CREDIT_RISK_DISTRIBUTION_TBL3" ("COUNTRY_DOMICILE_DESC" VARCHAR2(200), "DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(10), "ON_BAL_SHEET_EXP_ORIGINATED_CREDIT" NUMBER(20,2), "ON_BAL_SHEET_EXP_DEBT_INSTRUMENTS" NUMBER(20,2), "ON_BAL_SHEET_EXP_EQUITY" NUMBER(20,2), "OFF_BAL_SHEET_EXPOSURE" NUMBER(20,2), "GROSS_EXPOSURE" NUMBER(20,2), "MEMORANDUM_ITEM" NUMBER(20,2), "GROSS_EXPOSURE_PCT_QUAL_CAPITAL" NUMBER(20,4), "TOTAL_PROVISIONS" NUMBER(20,2), "SPECIFIC_PROVISIONS" NUMBER(20,2), "PORTFOLIO_GENERAL_PROVISIONS" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_BR340_CREDIT_RISK_DISTRIBUTION_TOTAL_TBL2
--------------------------------------------------------

  CREATE TABLE "QFCRA_BR340_CREDIT_RISK_DISTRIBUTION_TOTAL_TBL2" ("DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(10), "TOTAL" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_BR350_CREDIT_RISK_ASSETS_BOUGHT_TBL1
--------------------------------------------------------

  CREATE TABLE "QFCRA_BR350_CREDIT_RISK_ASSETS_BOUGHT_TBL1" ("DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(10,2), "DATE_BOUGHT_ACQUIRED" VARCHAR2(20), "NUMBER_OF_SHARES_HELD" NUMBER(20,2), "TYPE_OF_SHARES_HELD" VARCHAR2(50), "PERCENTAGE_INTEREST_HELD" NUMBER(20,4), "HISTORIC_COST_TO_DATE" NUMBER(20,2), "MARKET_VALUE_AT_RETURN_DATE" NUMBER(20,2), "NET_ASSET_VALUE_COMPANY" NUMBER(20,2), "NAV_DATE" VARCHAR2(20), "GRANTED" NUMBER(20,2), "UTILISED" NUMBER(20,2), "ATTRIBUTABLE_SHARE_PROFIT_LOSS" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_BR350_CREDIT_RISK_ASSETS_BOUGHT_TBL2
--------------------------------------------------------

  CREATE TABLE "QFCRA_BR350_CREDIT_RISK_ASSETS_BOUGHT_TBL2" ("DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(10,2), "DATE_BOUGHT_ACQUIRED" VARCHAR2(20), "NUMBER_OF_SHARES_HELD" NUMBER(20,2), "TYPE_OF_SHARES_HELD" VARCHAR2(50), "PERCENTAGE_INTEREST_HELD" NUMBER(20,4), "HISTORIC_COST_TO_DATE" NUMBER(20,2), "MARKET_VALUE_AT_RETURN_DATE" NUMBER(20,2), "NET_ASSET_VALUE_COMPANY" NUMBER(20,2), "NAV_DATE" VARCHAR2(20), "GRANTED" NUMBER(20,2), "UTILISED" NUMBER(20,2), "ATTRIBUTABLE_SHARE_PROFIT_LOSS" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_BR350_CREDIT_RISK_ASSETS_BOUGHT_TOTAL_TBL3
--------------------------------------------------------

  CREATE TABLE "QFCRA_BR350_CREDIT_RISK_ASSETS_BOUGHT_TOTAL_TBL3" ("DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(10,2), "DATE_BOUGHT_ACQUIRED" VARCHAR2(20), "NUMBER_OF_SHARES_HELD" NUMBER(20,2), "TYPE_OF_SHARES_HELD" VARCHAR2(50), "PERCENTAGE_INTEREST_HELD" NUMBER(20,4), "HISTORIC_COST_TO_DATE" NUMBER(20,2), "MARKET_VALUE_AT_RETURN_DATE" NUMBER(20,2), "NET_ASSET_VALUE_COMPANY" NUMBER(20,2), "NAV_DATE" VARCHAR2(20), "GRANTED" NUMBER(20,2), "UTILISED" NUMBER(20,2), "ATTRIBUTABLE_SHARE_PROFIT_LOSS" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_BR410_LIQ_RISK_ANTICIP_CHG_BUS_TBL3
--------------------------------------------------------

  CREATE TABLE "QFCRA_BR410_LIQ_RISK_ANTICIP_CHG_BUS_TBL3" ("DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(10), "CURRENT_PERIOD_BALANCE" NUMBER(20,2), "SIX_MONTH_FORECAST" NUMBER(20,2), "SIX_MONTH_ANNUALISED_PCT" NUMBER(20,4), "TWELVE_MONTH_FORECAST" NUMBER(20,2), "TWELVE_MONTH_PCT" NUMBER(20,4), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_BR410_LIQ_RISK_FIRM_SPEC_STRESS_MM_TBL1
--------------------------------------------------------

  CREATE TABLE "QFCRA_BR410_LIQ_RISK_FIRM_SPEC_STRESS_MM_TBL1" ("DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(10), "TOTAL" NUMBER(20,2), "NEXT_DAY" NUMBER(20,2), "DAYS_2_7" NUMBER(20,2), "DAYS_8_TO_1_MONTH" NUMBER(20,2), "MONTHS_1_TO_2" NUMBER(20,2), "GT_2_MONTHS" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_BR410_LIQ_RISK_STRESS_FUNDING_SRC_TBL2
--------------------------------------------------------

  CREATE TABLE "QFCRA_BR410_LIQ_RISK_STRESS_FUNDING_SRC_TBL2" ("DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(10), "TOTAL" NUMBER(20,2), "NEXT_DAY" NUMBER(20,2), "DAYS_2_7" NUMBER(20,2), "DAYS_8_TO_1_MONTH" NUMBER(20,2), "MONTHS_1_TO_2" NUMBER(20,2), "GT_2_MONTHS" NUMBER(20,2), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_DECL_FORM_TBL1
--------------------------------------------------------

  CREATE TABLE "QFCRA_DECL_FORM_TBL1" ("DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(10), "A" VARCHAR2(50), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_DECL_FORM_TBL1_PIIB2
--------------------------------------------------------

  CREATE TABLE "QFCRA_DECL_FORM_TBL1_PIIB2" ("DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(10), "A" VARCHAR2(50), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_DECL_FORM_TBL1_PIIB5
--------------------------------------------------------

  CREATE TABLE "QFCRA_DECL_FORM_TBL1_PIIB5" ("DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(10), "A" VARCHAR2(50), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_DECL_FORM_TBL2
--------------------------------------------------------

  CREATE TABLE "QFCRA_DECL_FORM_TBL2" ("DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(10), "B" VARCHAR2(50), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_DECL_FORM_TBL2_PIIB2
--------------------------------------------------------

  CREATE TABLE "QFCRA_DECL_FORM_TBL2_PIIB2" ("DESCRIPTION" VARCHAR2(200), "CODE" NUMBER(10), "B" VARCHAR2(50), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_SCOPE_OF_FILING
--------------------------------------------------------

  CREATE TABLE "QFCRA_SCOPE_OF_FILING" ("DESCRIPTION" VARCHAR2(500), "CODE" NUMBER(10), "A" VARCHAR2(50), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table QFCRA_SCOPE_OF_FILING_PIIB2
--------------------------------------------------------

  CREATE TABLE "QFCRA_SCOPE_OF_FILING_PIIB2" ("DESCRIPTION" VARCHAR2(500), "CODE" NUMBER(10), "A" VARCHAR2(50), "RDATE" DATE);

--------------------------------------------------------
--  DDL for Table RBI_MASTER
--------------------------------------------------------

  CREATE TABLE "RBI_MASTER" ("Id" NUMBER(11), "Name" VARCHAR2(50), "IsActiveStatus" VARCHAR2(10));

--------------------------------------------------------
--  DDL for Table RBI_MASTER_STATUS
--------------------------------------------------------

  CREATE TABLE "RBI_MASTER_STATUS" ("ID" NUMBER(11), "MASTERID" NUMBER(11), "REQUESTDATETIME" TIMESTAMP(6), "PROCESSSTATUS" CHAR(1), "PROCESSCOMPLETIONTIME" TIMESTAMP(6), "RECORDCOUNT" NUMBER(11));

--------------------------------------------------------
--  DDL for Table REASON_FOR_CREDITEVENTS_MASTER
--------------------------------------------------------

  CREATE TABLE "REASON_FOR_CREDITEVENTS_MASTER" ("REASONS" VARCHAR2(1000));

--------------------------------------------------------
--  DDL for Table RESOLUTION_STATUS_MASTER_CIMS
--------------------------------------------------------

  CREATE TABLE "RESOLUTION_STATUS_MASTER_CIMS" ("RESOLUTION_PLAN_STATUS_MASTER" VARCHAR2(150));

--------------------------------------------------------
--  DDL for Table RFA_FRAUD_MASTER_CIMS
--------------------------------------------------------

  CREATE TABLE "RFA_FRAUD_MASTER_CIMS" ("WH_CLASS_RFA_FRAUD" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table RPTSTATUS_GI
--------------------------------------------------------

  CREATE TABLE "RPTSTATUS_GI" ("CODE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table SECTOR_CODE_MASTERRLC_CIMS
--------------------------------------------------------

  CREATE TABLE "SECTOR_CODE_MASTERRLC_CIMS" ("SECTOR_CODE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table SECTOR_CODE_MASTER_CIMS
--------------------------------------------------------

  CREATE TABLE "SECTOR_CODE_MASTER_CIMS" ("SECTOR_CODE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table SMA_MASTER_CIMS
--------------------------------------------------------

  CREATE TABLE "SMA_MASTER_CIMS" ("SMA" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table STATE_CODE_INFO
--------------------------------------------------------

  CREATE TABLE "STATE_CODE_INFO" ("SR_NO" VARCHAR2(100), "STATE_NAME" VARCHAR2(200), "STATE_CODE" VARCHAR2(100), "TIN_NO" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table STATE_MASTER_CIMS
--------------------------------------------------------

  CREATE TABLE "STATE_MASTER_CIMS" ("STATENAME" VARCHAR2(200), "STATECODE" VARCHAR2(200), "REGIONNAME" VARCHAR2(200), "REGIONCODE" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table STATE_PINCODE_INFO
--------------------------------------------------------

  CREATE TABLE "STATE_PINCODE_INFO" ("PIN_CODE" VARCHAR2(100), "DIVISION_NAME" VARCHAR2(100), "REGION_NAME" VARCHAR2(100), "CIRCLE_NAME" VARCHAR2(100), "TALUK" VARCHAR2(100), "DISTRICT_NAME" VARCHAR2(100), "STATE_NAME" VARCHAR2(200), "TIN_NO" VARCHAR2(100), "STATE_CODE" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table STATE_PINCODE_INFORMATION
--------------------------------------------------------

  CREATE TABLE "STATE_PINCODE_INFORMATION" ("PIN_CODE" VARCHAR2(100), "DIVISION_NAME" VARCHAR2(100), "REGION_NAME" VARCHAR2(100), "CIRCLE_NAME" VARCHAR2(100), "TALUK" VARCHAR2(100), "DISTRICT_NAME" VARCHAR2(100), "STATE_NAME" VARCHAR2(200), "TIN_NO" VARCHAR2(100), "STATE_CODE" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table STATUS_MASTER_CIMS
--------------------------------------------------------

  CREATE TABLE "STATUS_MASTER_CIMS" ("VALUE_TEXT" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table STUDENT_DEMO_DEST
--------------------------------------------------------

  CREATE TABLE "STUDENT_DEMO_DEST" ("SR_NO" NUMBER, "FULL_NAME" VARCHAR2(50), "GENDER" VARCHAR2(50), "AGE" NUMBER, "CITY" VARCHAR2(50), "DOB" DATE);

--------------------------------------------------------
--  DDL for Table STUDENT_DEMO_SOURCE
--------------------------------------------------------

  CREATE TABLE "STUDENT_DEMO_SOURCE" ("SR_NO" NVARCHAR2(40), "FULL_NAME" VARCHAR2(50), "GENDER" VARCHAR2(20), "AGE" VARCHAR2(20), "CITY" VARCHAR2(50), "DOB" VARCHAR2(50));

--------------------------------------------------------
--  DDL for Table SUBSIDIARY_MASTER_CIMS
--------------------------------------------------------

  CREATE TABLE "SUBSIDIARY_MASTER_CIMS" ("BANKCODE" VARCHAR2(200), "BANKNAME" VARCHAR2(200), "INSTITUTION_CODE" VARCHAR2(200), "INSTITUTE_NAME" VARCHAR2(200), "AREA_OF_OPERATION" VARCHAR2(200), "ACTIVITY_NAME" VARCHAR2(200), "CATEGORY" VARCHAR2(200), "REGULATOR" VARCHAR2(200), "COUNTRY_NAME" VARCHAR2(200), "COUNTRY_CODE" VARCHAR2(200), "ACTIVE_FLG" VARCHAR2(200), "DETAILS_OF_ADD_DEL_MOD_REQ" VARCHAR2(200), "REASONS_FOR_CHANGE" VARCHAR2(200), "HOLDINGS" VARCHAR2(200), "QUERIES" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table TBL_API_REQUEST
--------------------------------------------------------

  CREATE TABLE "TBL_API_REQUEST" ("REQUEST_ID" VARCHAR2(1020), "COMPANY_ID" VARCHAR2(1020), "END_TIME" TIMESTAMP(6), "INPUT_FILE" VARCHAR2(1020), "OUTPUT_FILE" VARCHAR2(1020), "PARENT_REQUEST_ID" VARCHAR2(1020), "REQUESTURL" VARCHAR2(1020), "REQUESTING_USER_USERNAME" VARCHAR2(1020), "START_TIME" TIMESTAMP(6), "STATUS" NUMBER(10));

--------------------------------------------------------
--  DDL for Table TBL_CATEGORY
--------------------------------------------------------

  CREATE TABLE "TBL_CATEGORY" ("CATEGORY_ID" NUMBER(10), "CATEGORY_NAME" VARCHAR2(600), "CATEGORY_CODE" VARCHAR2(200), "IS_ACTIVE" CHAR(1), "CREATED_BY_FK" NUMBER(10), "CREATED_ON" TIMESTAMP(6), "LAST_MODIFIED_BY_FK" NUMBER(10), "LAST_MODIFIED_ON" TIMESTAMP(6), "LAST_APPROVED_BY_FK" NUMBER(10), "LAST_APPROVED_ON" TIMESTAMP(6), "LAST_UPDATE_ON" TIMESTAMP(6), "IS_BULK_UPLOAD" CHAR(1));

--------------------------------------------------------
--  DDL for Table TBL_DYNAMIC_CUSTOM_VAL_LABEL
--------------------------------------------------------

  CREATE TABLE "TBL_DYNAMIC_CUSTOM_VAL_LABEL" ("CUSTOM_VAL_LABEL_ID" NUMBER(10), "DYNA_VAL_MASTER_ID_FK" NUMBER(10), "CUSTOM_TAG" VARCHAR2(20), "LABEL_EN" VARCHAR2(100), "LABEL_HI" VARCHAR2(100), "IS_ACTIVE" CHAR(1));

--------------------------------------------------------
--  DDL for Table TBL_DYNAMIC_DATA
--------------------------------------------------------

  CREATE TABLE "TBL_DYNAMIC_DATA" ("DYNAMIC_DATA_ID" NUMBER(10), "DYNA_ELR_TABLE_ID_FK" NUMBER(10), "ELE_COL_MAPPING_ID_FK" NUMBER(10), "FACT_VALUE" VARCHAR2(4000));

--------------------------------------------------------
--  DDL for Table TBL_DYNAMIC_ELE_COL_INFO
--------------------------------------------------------

  CREATE TABLE "TBL_DYNAMIC_ELE_COL_INFO" ("ELE_COL_MAPPING_ID" NUMBER(10), "ELE_COL_TAG" VARCHAR2(5), "DYNA_ELR_TABLE_ID_FK" NUMBER(10), "ELE_NAME_ENG" VARCHAR2(250), "ELE_NAME_HI" VARCHAR2(250), "COL_NAME_ENG" VARCHAR2(250), "COL_NAME_HI" VARCHAR2(250), "XBRL_TAG" VARCHAR2(150), "EXPLICIT_MEMBER" VARCHAR2(4000), "TYPED_MEMBER" VARCHAR2(4000), "TABLE_NAME" VARCHAR2(45), "COLUMN_NAME" VARCHAR2(45), "IS_MANDATORY" CHAR(1), "REGEX_CHECK" VARCHAR2(50), "IS_ACTIVE" CHAR(1));

--------------------------------------------------------
--  DDL for Table TBL_DYNAMIC_ELR_INFO
--------------------------------------------------------

  CREATE TABLE "TBL_DYNAMIC_ELR_INFO" ("ELR_ID" NUMBER(10), "ELR_TAG" VARCHAR2(100), "ELR_LABLE_EN" VARCHAR2(150), "ELR_LABEL_HI" VARCHAR2(150), "IS_ACTIVE" CHAR(1), "RETURN_ID_FK" NUMBER(10));

--------------------------------------------------------
--  DDL for Table TBL_DYNAMIC_ELR_TABLE_INFO
--------------------------------------------------------

  CREATE TABLE "TBL_DYNAMIC_ELR_TABLE_INFO" ("TABLE_ID" NUMBER(10), "ELR_ID_FK" NUMBER(10), "TABLE_LABEL_EN" VARCHAR2(100), "TABLE_LABEL_HI" VARCHAR2(100), "IS_ACTIVE" CHAR(1));

--------------------------------------------------------
--  DDL for Table TBL_DYNAMIC_FACT
--------------------------------------------------------

  CREATE TABLE "TBL_DYNAMIC_FACT" ("DYNAMIC_FACT_ID" NUMBER(10), "VALUE_1" VARCHAR2(200), "VALUE_2" VARCHAR2(200), "VALUE_3" VARCHAR2(200), "VALUE_4" VARCHAR2(200), "VALUE_5" VARCHAR2(200), "VALUE_6" VARCHAR2(200), "VALUE_7" VARCHAR2(200), "VALUE_8" VARCHAR2(200), "VALUE_9" VARCHAR2(200), "VALUE_10" VARCHAR2(200), "VALUE_11" VARCHAR2(200), "VALUE_12" VARCHAR2(200), "VALUE_13" VARCHAR2(200), "VALUE_14" VARCHAR2(200), "VALUE_15" VARCHAR2(200), "VALUE_16" VARCHAR2(200), "VALUE_17" VARCHAR2(200), "VALUE_18" VARCHAR2(200), "VALUE_19" VARCHAR2(200), "VALUE_20" VARCHAR2(200), "VALUE_21" VARCHAR2(200), "VALUE_22" VARCHAR2(200), "VALUE_23" VARCHAR2(200), "VALUE_24" VARCHAR2(200), "VALUE_25" VARCHAR2(200), "VALUE_26" VARCHAR2(200), "VALUE_27" VARCHAR2(200), "VALUE_28" VARCHAR2(200), "VALUE_29" VARCHAR2(200), "VALUE_30" VARCHAR2(200), "VALUE_31" VARCHAR2(200), "VALUE_32" VARCHAR2(200), "VALUE_33" VARCHAR2(200), "VALUE_34" VARCHAR2(200), "VALUE_35" VARCHAR2(200), "VALUE_36" VARCHAR2(200), "VALUE_37" VARCHAR2(200), "VALUE_38" VARCHAR2(200), "VALUE_39" VARCHAR2(200), "VALUE_40" VARCHAR2(200), "VALUE_41" VARCHAR2(200), "VALUE_42" VARCHAR2(200), "VALUE_43" VARCHAR2(200), "VALUE_44" VARCHAR2(200), "VALUE_45" VARCHAR2(200), "VALUE_46" VARCHAR2(200), "VALUE_47" VARCHAR2(200), "VALUE_48" VARCHAR2(200), "VALUE_49" VARCHAR2(200), "VALUE_50" VARCHAR2(200), "VALUE_51" VARCHAR2(200), "VALUE_52" VARCHAR2(200), "VALUE_53" VARCHAR2(200), "VALUE_54" VARCHAR2(200), "VALUE_55" VARCHAR2(200), "VALUE_56" VARCHAR2(200), "VALUE_57" VARCHAR2(200), "VALUE_58" VARCHAR2(200), "VALUE_59" VARCHAR2(200), "VALUE_60" VARCHAR2(200), "VALUE_61" VARCHAR2(200), "VALUE_62" VARCHAR2(200), "VALUE_63" VARCHAR2(200), "VALUE_64" VARCHAR2(200), "VALUE_65" VARCHAR2(200), "VALUE_66" VARCHAR2(200), "VALUE_67" VARCHAR2(200), "VALUE_68" VARCHAR2(200), "VALUE_69" VARCHAR2(200), "VALUE_70" VARCHAR2(200), "TYPED_MEM_VAL_1" VARCHAR2(200), "TYPED_MEM_VAL_2" VARCHAR2(200), "TYPED_MEM_VAL_3" VARCHAR2(200), "TYPED_MEM_VAL_4" VARCHAR2(200), "TYPED_MEM_VAL_5" VARCHAR2(200), "TYPED_MEM_VAL_6" VARCHAR2(200), "TYPED_MEM_VAL_7" VARCHAR2(200), "TYPED_MEM_VAL_8" VARCHAR2(200), "TYPED_MEM_VAL_9" VARCHAR2(200), "TYPED_MEM_VAL_10" VARCHAR2(200), "DYNA_ELR_TABLE_ID_FK" NUMBER(10), "IS_ACTIVE" CHAR(1));

--------------------------------------------------------
--  DDL for Table TBL_DYNAMIC_MASTER_COL_INFO
--------------------------------------------------------

  CREATE TABLE "TBL_DYNAMIC_MASTER_COL_INFO" ("MASTER_ID" NUMBER(10), "MASTER_COL_TAG" VARCHAR2(100), "MASTER_COL_LABEL_EN" VARCHAR2(100), "MASTER_COL_LABEL_HI" VARCHAR2(100), "TABLE_NAME" VARCHAR2(45), "COLUMN_NAME" VARCHAR2(45), "DYNA_ELR_TABLE_ID_FK" NUMBER(10), "MASTER_ELE_TAG" VARCHAR2(10), "IS_ACTIVE" NUMBER(10));

--------------------------------------------------------
--  DDL for Table TBL_DYNAMIC_VALIDATION_ERROR
--------------------------------------------------------

  CREATE TABLE "TBL_DYNAMIC_VALIDATION_ERROR" ("DYNAMIC_VAL_ERROR_ID" NUMBER(10), "UPLOAD_ID_FK" NUMBER(10), "ERROR_JSON" CLOB, "ERROR_GENERATED_ON" TIMESTAMP(0));

--------------------------------------------------------
--  DDL for Table TBL_DYNAMIC_VAL_MASTER
--------------------------------------------------------

  CREATE TABLE "TBL_DYNAMIC_VAL_MASTER" ("VAL_MASTER_ID" NUMBER(10), "FORMULA" CLOB, "TYPE" VARCHAR2(20), "IS_ACTIVE" CHAR(1), "RETURN_ID_FK" NUMBER(10), "CATEGORY_ID_FK" NUMBER(10));

--------------------------------------------------------
--  DDL for Table TBL_ENTITY
--------------------------------------------------------

  CREATE TABLE "TBL_ENTITY" ("ENTITY_ID" NUMBER(10), "ENTITY_NAME" VARCHAR2(600), "ENTITY_SHORT_NAME" VARCHAR2(200), "ENTITY_CODE" VARCHAR2(15), "IFSC_CODE" VARCHAR2(45), "BANK_WORKING_CODE" VARCHAR2(45), "COMP_TYPE_ID_FK" NUMBER(10), "CATEGORY_ID_FK" NUMBER(10), "SUB_CATEGORY_ID_FK" NUMBER(10), "OP_LEVEL1" VARCHAR2(200), "OP_LEVEL2" VARCHAR2(200), "OP_LEVEL3" VARCHAR2(200), "OP_LEVEL4" VARCHAR2(200), "OP_LEVEL5" VARCHAR2(200), "ENTITY_EMAIL_ID" VARCHAR2(600), "IS_ACTIVE" CHAR(1), "CREATED_BY_FK" NUMBER(10), "CREATED_ON" TIMESTAMP(6), "LAST_MODIFIED_BY_FK" NUMBER(10), "LAST_MODIFIED_ON" TIMESTAMP(6), "LAST_APPROVED_BY_FK" NUMBER(10), "LAST_APPROVED_ON" TIMESTAMP(6), "ENTITY_PHONE_NO" VARCHAR2(20), "LAST_UPDATE_ON" TIMESTAMP(6), "ENTITY_URL" VARCHAR2(600), "FIN_YR_FORMAT_ID_FK" NUMBER(10), "ENTITY_NAME_BIL" VARCHAR2(600), "ENTITY_SHORT_NAME_BIL" VARCHAR2(600), "REGISTRATION_DATE" TIMESTAMP(0), "AUTHORIZED_CAPITAL" VARCHAR2(20), "PAID_UP_CAPITAL" VARCHAR2(20), "IN_KIND_CAPITAL" VARCHAR2(20), "ISSUANCE_MANAGER_ID_FK" NUMBER(10), "BRANCH_DTL" VARCHAR2(50), "COMPANY_LEGAL_STATUS" NUMBER(10), "IS_REGISTER" CHAR(1), "IS_ISLAMIC" CHAR(1), "IS_SPV" CHAR(1), "IS_MEMBER" CHAR(1), "SIGNATURES_FORM" VARCHAR2(50), "OTC" CHAR(1), "OTHER_INFO_ATTACHMENT" VARCHAR2(50), "IS_GOVERNMENT" CHAR(1), "IS_BULK_UPLOAD" NUMBER(1), "ENTITY_SYMBOL_CODE" VARCHAR2(10), "ENTITY_ADDRESS" VARCHAR2(200), "BANK_TYPE_ID_FK" NUMBER(10), "IS_NBFC_ENTITY" CHAR(1));

--------------------------------------------------------
--  DDL for Table TBL_QUALIFYING_AND_COVERED_DEPOSITS
--------------------------------------------------------

  CREATE TABLE "TBL_QUALIFYING_AND_COVERED_DEPOSITS" ("SRNO" NUMBER, "BANKCODE" VARCHAR2(20), "REPORTINGDATE" VARCHAR2(20), "TOTAL_COVERED_DEPOSITS" NUMBER(20,2), "TOTAL_QUALIFYING_DEPOSITS" NUMBER(20,2));

--------------------------------------------------------
--  DDL for Table TBL_RETURN
--------------------------------------------------------

  CREATE TABLE "TBL_RETURN" ("RETURN_ID" NUMBER(10), "RETURN_NAME" VARCHAR2(1000), "RETURN_CODE" VARCHAR2(200), "MOD_RET_CODE" VARCHAR2(200), "FREQUENCY_ID_FK" NUMBER(10), "IS_PARENT" CHAR(1), "IS_PARENT_ID_FK" NUMBER(10), "IS_ACTIVE" CHAR(1), "ALLOW_REVISION" CHAR(1), "CREATED_BY_FK" NUMBER(10), "CREATED_ON" TIMESTAMP(6), "LAST_MODIFIED_BY_FK" NUMBER(10), "LAST_MODIFIED_ON" TIMESTAMP(6), "LAST_APPROVED_BY_FK" NUMBER(10), "LAST_APPROVED_ON" TIMESTAMP(6), "LAST_UPDATE_ON" TIMESTAMP(6), "IS_BULK_UPLOAD" CHAR(1), "IS_NON_XBRL" CHAR(1), "FORMULA_FILE_NAME" VARCHAR2(200), "DELAY_CRITERIA_FILE_NAME" VARCHAR2(200), "RETURN_GROUP_MAP_ID_FK" NUMBER(10), "RETURN_TEMPLATE_NAME" VARCHAR2(200), "ERROR_COUNT" NUMBER(10), "WARNING_COUNT" NUMBER(10), "RETURN_PROPERTY_ID_FK" NUMBER(10), "EXCEL_READ_JSON" VARCHAR2(4000), "MAX_REVISION_REQ_DAYS" NUMBER(10), "MAX_UNLOCK_REQ_DAYS" NUMBER(10), "MAX_REVISION_COUNT" NUMBER(10), "OLD_RETURN_CODE" VARCHAR2(45), "RETURN_DOC_ID" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table TBL_RETURNS_UPLOAD_DETAILS
--------------------------------------------------------

  CREATE TABLE "TBL_RETURNS_UPLOAD_DETAILS" ("UPLOAD_ID" NUMBER(10), "RETURN_ID_FK" NUMBER(10), "ENTITY_ID_FK" NUMBER(10), "FILING_STATUS_ID_FK" NUMBER(10), "PREVIOUS_UPLOAD_ID" NUMBER(10), "REVISION_REQUEST_ID_FK" NUMBER(10), "UNLOCK_REQUEST_ID_FK" NUMBER(10), "INSTANCE_FILE" VARCHAR2(500), "VALIDATION_FAIL_REPORT_FILE" VARCHAR2(500), "FORM_VERSION_ID" NUMBER(10), "START_DATE" DATE, "END_DATE" DATE, "UPLOADED_DATE" TIMESTAMP(6), "UPLOADED_BY" NUMBER(10), "FIN_YR_FREQUENCY_DESC_ID_FK" NUMBER(10), "ISACTIVE" CHAR(1), "IS_NILLABLE" CHAR(1), "NILLABLE_COMMENTS" VARCHAR2(400), "APPROVAL_ROLE_ID_FK" VARCHAR2(100), "CURRENT_WF_STEP" NUMBER(10), "WORKFLOW_ID_FK" NUMBER(10), "APPROVAL_RESULT" VARCHAR2(50), "ASSIGNED_TO" NUMBER(10), "ASSIGNED_ON" TIMESTAMP(6), "ASSIGNED_TO_ROLE" NUMBER(10), "DBFLAG" CHAR(1), "UPLOAD_USER_ROLE" NUMBER(10), "JSON_DATA" VARCHAR2(500), "ATTACHED_FILE_NAME" VARCHAR2(500), "COMPARISON_JSON_DATA" CLOB, "RETURN_ID" NUMBER(10), "FIN_YR_FREQUENCY_ID_FK" NUMBER(10), "CONVERSION_RATE" NUMBER(10), "REPORTING_CURRENCY" VARCHAR2(100), "UPLOAD_CHANNEL_ID_FK" NUMBER(10), "RETURN_PROPERTY_VAL_ID_FK" NUMBER(10), "FILE_TYPE" VARCHAR2(100), "FILE_DETAILS_ID_FK" NUMBER(10), "LAST_UPDATE_DATE" TIMESTAMP(0), "RETURN_PROP_VAL_ID_FK" NUMBER(10), "CONSISTANCY_CHECK_JSON" CLOB, "IS_CONSISTANCY_CHECK_FAILURE" CHAR(1), "NO_OF_ERRORS" NUMBER(10), "NO_OF_WARNINGS" NUMBER(10), "SDMX_EBR_RBR_PREP_ID_FK" NUMBER(10));

--------------------------------------------------------
--  DDL for Table TEMP_DECIMAL_VALID_FOR_TEST
--------------------------------------------------------

  CREATE TABLE "TEMP_DECIMAL_VALID_FOR_TEST" ("SR_NO" NUMBER, "NAME" VARCHAR2(30), "SAL" VARCHAR2(32));

--------------------------------------------------------
--  DDL for Table TEMP_IDEALCENTRAL
--------------------------------------------------------

  CREATE TABLE "TEMP_IDEALCENTRAL" ("DESCRIPTION" VARCHAR2(2000), "VAL" VARCHAR2(250), "CODE" VARCHAR2(1205));

--------------------------------------------------------
--  DDL for Table TEMP_IDEALDB
--------------------------------------------------------

  CREATE TABLE "TEMP_IDEALDB" ("DESCRIPTION" VARCHAR2(2000), "CODE" VARCHAR2(1205), "VAL" VARCHAR2(250), "CODE1" VARCHAR2(180));

--------------------------------------------------------
--  DDL for Table TEST
--------------------------------------------------------

  CREATE TABLE "TEST" ("PARTICULARS" VARCHAR2(500), "ABC" NUMBER);

--------------------------------------------------------
--  DDL for Table TESTCSV
--------------------------------------------------------

  CREATE TABLE "TESTCSV" ("RETURNNAME" VARCHAR2(100), "RETURNCODE" VARCHAR2(100), "BANKNAME" VARCHAR2(100), "BANKCODE" VARCHAR2(100), "FREQ" VARCHAR2(20), "REPDATE" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table TEST_SARB
--------------------------------------------------------

  CREATE TABLE "TEST_SARB" ("SRNO" VARCHAR2(500), "BANK_CODE" VARCHAR2(100), "SIMPLE_ACC_QULIFYING_DEPOSIT" VARCHAR2(100), "SIMPLE_ACC_COVERED_DEPOSIT" VARCHAR2(100), "FM_BENEFICIARY_ACC_QULIFYING_DEPOSIT" VARCHAR2(100), "FM_BENEFICIARY_ACC_COVERED_DEPOSIT" VARCHAR2(100), "INFM_BENEFICIARY_ACC_QULIFYING_DEPOSIT" VARCHAR2(100), "INFM_BENEFICIARY_ACC_COVERED_DEPOSIT" VARCHAR2(100), "TOTAL_QULIFYING_DEPOSIT" VARCHAR2(100), "TOTAL_OVERED_DEPOSIT" VARCHAR2(100), "TOT_OVERED_AS_PERCENTAGE_QULIFYING" VARCHAR2(100), "RPDATE" DATE, "RDATE" VARCHAR2(20));

--------------------------------------------------------
--  DDL for Table TF_R_1
--------------------------------------------------------

  CREATE TABLE "TF_R_1" ("AD_CODE" VARCHAR2(200), "FORTNIGHT_END_DATE" VARCHAR2(200), "TRANSACTION_DATE" VARCHAR2(200), "SERIAL_NO" VARCHAR2(200), "PURPOSE_CODE" VARCHAR2(200), "COUNTRY_CODE" VARCHAR2(200), "CURRENCY_CODE" VARCHAR2(200), "AMOUNT_IN_FC" VARCHAR2(200), "DATE_OF_SHIPMENT" VARCHAR2(200), "LC" VARCHAR2(200), "TEMP1" VARCHAR2(200), "COUNTRY_OF_VOSTRO" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table TF_R_2
--------------------------------------------------------

  CREATE TABLE "TF_R_2" ("AD_CODE" VARCHAR2(200), "FORTNIGHT_END_DATE" VARCHAR2(200), "SERIAL_NO" VARCHAR2(200), "PURPOSE_CODE" VARCHAR2(200), "COUNTRY_OF_VOSTRO" VARCHAR2(200), "CURRENCY" VARCHAR2(200), "AMOUNT_IN_Currency" VARCHAR2(200), "Return" VARCHAR2(200));

--------------------------------------------------------
--  DDL for Table TOP_1000_BORROWER_MASTER_CIMS
--------------------------------------------------------

  CREATE TABLE "TOP_1000_BORROWER_MASTER_CIMS" ("SR_NO" VARCHAR2(20), "BORROWER_PAN" VARCHAR2(250), "BORROWER_NAME" VARCHAR2(250), "INDUSTRY_CODE" VARCHAR2(250), "INDUSTRY_DESCRIPTION" VARCHAR2(250), "GROUP_CODE" VARCHAR2(250), "GROUP_NAME" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table USERS
--------------------------------------------------------

  CREATE TABLE "USERS" ("ID" NUMBER(19), "PASSWORD" VARCHAR2(1020), "USERNAME" VARCHAR2(1020));

--------------------------------------------------------
--  DDL for Table VALIDATE_INTEGER
--------------------------------------------------------

  CREATE TABLE "VALIDATE_INTEGER" ("PAN" VARCHAR2(250), "SHEET_NAME" VARCHAR2(250), "COLUMN_NAME" VARCHAR2(250), "VALUE" VARCHAR2(250), "SRNO" NUMBER, "ERROR_DESCRIPTION" VARCHAR2(1000));

--------------------------------------------------------
--  DDL for Table VALIDATIONDTL
--------------------------------------------------------

  CREATE TABLE "VALIDATIONDTL" ("SR_NO" NUMBER, "ERROR_EXCEL" VARCHAR2(250), "ERROR_SHEET" VARCHAR2(250), "ERROR_DESC" VARCHAR2(500), "ERROR_COLUMN" VARCHAR2(250), "ERROR_VALUE" VARCHAR2(250), "KEY_FIELD" VARCHAR2(250), "KEY_FIELD_VALUE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table VALIDATIONDTL_CIMS
--------------------------------------------------------

  CREATE TABLE "VALIDATIONDTL_CIMS" ("SR_NO" NUMBER, "ERROR_EXCEL" VARCHAR2(250), "ERROR_SHEET" VARCHAR2(250), "ERROR_DESC" VARCHAR2(500), "ERROR_COLUMN" VARCHAR2(250), "ERROR_VALUE" VARCHAR2(250), "KEY_FIELD" VARCHAR2(250), "KEY_FIELD_VALUE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table VALIDATIONDTL_JIGS
--------------------------------------------------------

  CREATE TABLE "VALIDATIONDTL_JIGS" ("SR_NO" NUMBER, "ERROR_EXCEL" VARCHAR2(250), "ERROR_SHEET" VARCHAR2(250), "ERROR_DESC" VARCHAR2(500), "ERROR_COLUMN" VARCHAR2(250), "ERROR_VALUE" VARCHAR2(250), "KEY_FIELD" VARCHAR2(250), "KEY_FIELD_VALUE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table VALIDATIONDTL_WARNING
--------------------------------------------------------

  CREATE TABLE "VALIDATIONDTL_WARNING" ("SR_NO" NUMBER(11), "ERROR_EXCEL" VARCHAR2(100), "ERROR_SHEET" VARCHAR2(100), "ERROR_DESC" VARCHAR2(500), "ERROR_COLUMN" VARCHAR2(100), "ERROR_VALUE" VARCHAR2(100), "KEY_FIELD" VARCHAR2(100), "KEY_FIELD_VALUE" VARCHAR2(100));

--------------------------------------------------------
--  DDL for Table VALIDATION_SETTING_M_ORG
--------------------------------------------------------

  CREATE TABLE "VALIDATION_SETTING_M_ORG" ("SRNO" NUMBER, "EXCEL_NAME" VARCHAR2(150), "EXCEL_SHEET" VARCHAR2(150), "VAL_TABLE" VARCHAR2(150), "VAL_COLUMN" VARCHAR2(150), "COMPARE_TABLE" VARCHAR2(150), "COMPARE_COLUMN" VARCHAR2(150), "KEY_COLUMN" VARCHAR2(150), "VAL_TYPE" NUMBER);

--------------------------------------------------------
--  DDL for Table VALIDATION_TEMP_JIGS
--------------------------------------------------------

  CREATE TABLE "VALIDATION_TEMP_JIGS" ("SR_NO" NUMBER, "ERROR_EXCEL" VARCHAR2(250), "ERROR_SHEET" VARCHAR2(250), "ERROR_DESC" VARCHAR2(500), "ERROR_COLUMN" VARCHAR2(250), "ERROR_VALUE" VARCHAR2(250), "KEY_FIELD" VARCHAR2(250), "KEY_FIELD_VALUE" VARCHAR2(250));

--------------------------------------------------------
--  DDL for Table XBRLV
--------------------------------------------------------

  CREATE TABLE "XBRLV" ("ASONDATE" DATE, "XBRL_SLNO" NUMBER(38), "CODE_TYPE" VARCHAR2(5), "CODE_VALUE" VARCHAR2(500), "CMUSER" VARCHAR2(10), "CMDATE" DATE);
