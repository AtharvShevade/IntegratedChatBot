"""iDEAL 6.0 entity schema — tenant-scoped repo, renamed files/attributes.

Mirrors v5_5_schema.py's logical field names so every downstream reader
(query_handlers.py, extractors.py, auth_service.py, report_lookup.py) keeps
working against the same logical keys regardless of APP_VERSION — only the
on-disk filename / row tag / raw attribute name changes here.

Verified directly against D:\\Repo6\\Repo6\\1001\\DataBase\\*.xml. Entities
not listed here (providers, segments, bank_details, audit, error_log,
uploaded_file_log, cross_validation_log, nonxbrl_returns) are assumed
unchanged from 5.5's filename/attributes — not yet confirmed against real
6.0 data; the loader degrades to [] with a logged warning if that
assumption is wrong, rather than raising.
"""
from __future__ import annotations

from backend.db_qa.versions.loader import EntitySpec

SCHEMA: dict[str, EntitySpec] = {

    "users": EntitySpec(
        filename="User.xml",
        row_tag="Row",
        attribute_map={
            "UserId": "Id",
            "Name": "FirstName",
            "EmailId": "EmailId",
            "RoleId": "RoleId",
            "DepartmentId": "DepartmentId",
            "LoginId": "LoginId",
            "Status": "Status",
            "QuestionId": "QuestionId",
            "LastLoginDT": "LastLoginDT",
            "PasswordUpdateDate": "PasswordUpdateDate",
            "FailedLoginCount": "FailedLoginCount",
            "ActionBy": "ActionBy",
            "ActionDate": "ActionDate",
            "LastFailedLoginDT": "LastFailedLoginDT",
            "MobileNumber": "PhoneNumber",
            # Password, SecondPassword..FifthPassword, Answer, RefreshToken,
            # RefreshTokenExpiryTime are intentionally NEVER mapped here.
        },
    ),

    "departments": EntitySpec(
        filename="Department.xml",
        row_tag="Row",
        attribute_map={
            "DeptId": "Id",
            "Name": "Name",
            "EmailId": "Email",
            "Status": "Status",
            "Forms": "ReturnId",
            "NXForms": "NXReturnId",
        },
    ),

    "roles": EntitySpec(
        filename="Role.xml",
        row_tag="Row",
        attribute_map={
            "RoleId": "Id",
            "Name": "Name",
            "Status": "Status",
        },
    ),

    "role_access": EntitySpec(
        filename="RoleAccess.xml",
        row_tag="Row",
        attribute_map={
            "OptionId": "OptionId",
            "RoleId": "RoleId",
            "HasNew": "HasNew",
            "HasEdit": "HasEdit",
            "HasView": "HasView",
            "HasApprove": "HasApprove",
        },
    ),

    "returns": EntitySpec(
        filename="Return.xml",
        row_tag="Row",
        attribute_map={
            "Id": "Id",
            "Name": "Name",
            "InstanceNameSpace": "InstanceNameSpace",
            "TaxonomyNameSpace": "TaxonomyNameSpace",
            "PeriodId": "PeriodId",
            "Status": "Status",
            "IsValidated": "IsValidated",
            "IsEncryptionReq": "IsEncryptionReq",
            "IsSchCalValidation": "IsSchCalValidation",
            "Version": "Version",
            "BaseFileName": "BaseFileName",
            "Href": "Href",
            "XSDPath": "XSDPath",
            "IsFormulaValidation": "IsFormulaValidation",
            "IsLargeValidator": "IsLargeValidator",
            "IsRBIValidation": "IsRBIValidation",
            "RepFreq": "RepFreq",
            "IsCims": "IsCims",
            "IsTBL": "IsTBL",
            "IsExcel": "IsExcel",
            # 6.0 has no separate ReturnId attribute — Id serves both the
            # FormId and ReturnId role (confirmed: the .NET DTO's ReturnId
            # field is populated with the FormId value). Callers needing a
            # "ReturnId for this FormId" must special-case IS_V6 and reuse
            # the FormId itself instead of reading this key.
            "ReturnId": None,
            "AltName": "AltName",
            "DueDays": "DueDays",
        },
    ),

    "nonxbrl_returns": EntitySpec(
        filename="NonXBRLReturn.xml",
        row_tag="Row",
        attribute_map={
            "Id": "Id",
            "Name": "Name",
            "PeriodId": "PeriodId",
            "DueDays": "DueDays",
            "Status": "Status",
            "ReturnId": None,
            "JobProcessingId": "JobProcessingId",
            "IsCims": "IsCims",
            "HasFolder": "HasFolder",
        },
    ),

    "options": EntitySpec(
        filename="Option.xml",
        row_tag="Row",
        attribute_map={
            "OptionId": "Id",
            "OptionName": "Name",
            "ParentOptionId": "ParentOptionId",
            "Rank": "Rank",
            "Icon": "Icon",
            "IsMenu": None,
            "ResourceId": "ResourceId",
            "CanNew": "CanNew",
            "CanEdit": "CanEdit",
            "CanView": "CanView",
            "CanApprove": "CanApprove",
        },
    ),

    "periods": EntitySpec(
        filename="Period.xml",
        row_tag="Row",
        attribute_map={
            "Period_Id": "Id",
            "Frequency": "Frequency",
            "EBRFrequency": None,
            "PeriodName": "PeriodName",
            "AdvanceNotificationDays": None,
        },
    ),

    "providers": EntitySpec(
        filename="XML_Providers.xml",
        row_tag="Row",
        attribute_map={
            "ProviderId": "ProviderId",
            "ProviderName": "ProviderName",
            "ProviderType": "ProviderType",
            "IsActive": "IsActive",
        },
    ),

    "instance_log": EntitySpec(
        filename="InstanceLog.xml",
        row_tag="Row",
        attribute_map={
            "Id": "Id",
            "InsCompare": None,
            "RequestId": None,
            "FormId": "ReturnId",
            "DTC": "CreateDT",
            "FileUploadDT": None,
            "ReportStartDT": "ReportStartDT",
            "ReportEndDT": "ReportEndDT",
            "ReportingDate": "ReportingDate",
            "Status": "Status",
            "UserId": "CreatedBy",
            "InstanceDocPath": "InstanceDoc",
            "EncryptDocPath": "EncryptDoc",
            "ErrorDocPath": "ErrorDoc",
            "RenderedExcelDocPath": "RenderDoc",
            "IsExtract": "IsExtract",
            "IsInstance": "IsInstance",
            "IsCims": None,
            "IsAudited": None,
            "ApprovedBy": "ApprovedBy",
            "ApprovedDt": "ApprovedDT",
            "CIMSUploadBy": None,
            "CIMSUploadDT": None,
            "CIMSUploadStatus": None,
            "RejectComment": None,
            "Comment": "Comment",
        },
    ),

    "nonxbrl_instance_log": EntitySpec(
        filename="NxInstanceLog.xml",
        row_tag="Row",
        attribute_map={
            "Id": "Id",
            "FormId": "ReturnId",
            "VersionSelected": None,
            "DTC": "CreateDT",
            "FileUploadDT": None,
            "ReportStartDT": "ReportStartDT",
            "ReportEndDT": "ReportEndDT",
            "ReportingDate": "ReportingDate",
            "Status": "Status",
            "UserId": "CreatedBy",
            "InstanceDocPath": "InstanceDoc",
            "ErrorDocPath": "ErrorDoc",
            "RenderedDocPath": "RenderDoc",
            "IsExtract": "IsExtract",
            "IsInstance": "IsInstance",
            "IsCims": None,
            "IsAudited": None,
            "ApprovedBy": "ApprovedBy",
            "ApprovedDt": "ApprovedDT",
            "CIMSUploadBy": None,
            "CIMSUploadDT": None,
            "CIMSUploadStatus": None,
            "RejectComment": None,
            "Comment": "Comment",
        },
    ),

    "segments": EntitySpec(
        filename="XML_Segment.xml",
        row_tag="Row",
        attribute_map={
            "Segment_Id": "Segment_Id",
            "SegmentName": "SegmentName",
        },
    ),

    "bank_details": EntitySpec(
        filename="XML_BankDetail.xml",
        row_tag="Row",
        attribute_map={
            "BankCode": "BankCode",
            "BankName": "BankName",
            "BankType": "BankType",
            "CRR": "CRR",
        },
    ),

    "audit": EntitySpec(
        filename="XML_Audit.xml",
        row_tag="Row",
        attribute_map={
            "OptionId": "OptionId",
            "AuditDateTime": "AuditDateTime",
            "AuditType": "AuditType",
            "UserId": "UserId",
            "Remark": "Remark",
            "VersionSelected": "VersionSelected",
        },
    ),

    "error_log": EntitySpec(
        filename="XML_ErrorLog.xml",
        row_tag="Row",
        attribute_map={
            "OptionId": "OptionId",
            "OptionElementId": "OptionElementId",
            "AuditDateTime": "AuditDateTime",
            "UserId": "UserId",
            "Remark": "Remark",
        },
    ),

    "uploaded_file_log": EntitySpec(
        filename="XML_UploadedFileLog.xml",
        row_tag="Row",
        attribute_map={
            "Id": "Id",
            "FileName": "FileName",
            "DateTime": "DateTime",
            "UserId": "UserId",
        },
    ),

    "cross_validation_log": EntitySpec(
        filename="XML_CrossValidationLog.xml",
        row_tag="Row",
        attribute_map={
            "Id": "Id",
            "FirstInstanceName": "FirstInstanceName",
            "SecondInstanceName": "SecondInstanceName",
            "FirstReportName": "FirstReportName",
            "SecondReportName": "SecondReportName",
            "FileName": "FileName",
            "DTC": "DTC",
            "ReportingDate": "ReportingDate",
            "Status": "Status",
            "DownloadReport": "DownloadReport",
            "GeneratedBy": "GeneratedBy",
        },
    ),
}
