"""iDEAL 5.5 entity schema — identity attribute_map.

Every logical field name here IS the raw XML attribute name already read
throughout query_handlers.py and extractors.py. This file exists so the
loader has a uniform interface: `dict(row.attrib)` and
`_project_row(row, SCHEMA[e].attribute_map)` produce identical dicts (same
keys, same values), because attribute_map is an identity mapping everywhere
it isn't None (schema quirk).

Credential fields are never listed in any attribute_map below — this is
what keeps them out of every loaded row (see loader.load_entity).
"""
from __future__ import annotations

from backend.db_qa.versions.loader import EntitySpec

SCHEMA: dict[str, EntitySpec] = {

    "users": EntitySpec(
        filename="XML_User.xml",
        row_tag="Row",
        attribute_map={
            "UserId": "UserId",
            "Name": "Name",
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
            "MobileNumber": "MobileNumber",
            "CreatedBy": "CreatedBy",
            "UserCreationDate": "UserCreationDate",
            # Password, SecondPassword..FifthPassword, Answer, RefreshToken,
            # RefreshTokenExpiryTime are intentionally NEVER mapped here.
        },
    ),

    "departments": EntitySpec(
        filename="XML_Dept.xml",
        row_tag="Row",
        attribute_map={
            "DeptId": "DeptId",
            "Name": "Name",
            "EmailId": "EmailId",
            "Status": "Status",
            "Forms": "Forms",
            "NXForms": "NXForms",
            "Level1UserEmails": "Level1UserEmails",
            "Level2UserEmails": "Level2UserEmails",
            "Level3UserEmails": "Level3UserEmails",
        },
        # Forms/NXForms stay strings — handle_dept_returns() etc. call
        # .split("|") on them directly. list_fields intentionally empty.
    ),

    "roles": EntitySpec(
        filename="XML_Role.xml",
        row_tag="Row",
        attribute_map={
            "RoleId": "RoleId",
            "Name": "Name",
            "Status": "Status",
        },
    ),

    "role_access": EntitySpec(
        filename="XML_RoleAccess.xml",
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
        filename="Returns.xml",
        row_tag="Return",
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
            "ReturnId": "ReturnId",
            "AltName": "AltName",
            "DueDays": "DueDays",
        },
    ),

    "nonxbrl_returns": EntitySpec(
        filename="NonXBRLReturns.xml",
        row_tag="Return",
        attribute_map={
            "Id": "Id",
            "Name": "Name",
            "PeriodId": "PeriodId",
            "DueDays": "DueDays",
            "Status": "Status",
            "ReturnId": "ReturnId",
            "JobProcessingId": "JobProcessingId",
            "IsCims": "IsCims",
            "HasFolder": "HasFolder",
        },
    ),

    "options": EntitySpec(
        filename="XML_Option.xml",
        row_tag="Row",
        attribute_map={
            "OptionId": "OptionId",
            "OptionName": "OptionName",
            "ParentOptionId": "ParentOptionId",
            "Rank": "Rank",
            "Icon": "Icon",
            "IsMenu": "IsMenu",
            "ResourceId": "ResourceId",
            "CanNew": "CanNew",
            "CanEdit": "CanEdit",
            "CanView": "CanView",
            "CanApprove": "CanApprove",
        },
    ),

    "periods": EntitySpec(
        filename="XML_Period.xml",
        row_tag="Row",
        attribute_map={
            "Period_Id": "Period_Id",
            "Frequency": "Frequency",
            "EBRFrequency": "EBRFrequency",
            "PeriodName": "PeriodName",
            "AdvanceNotificationDays": "AdvanceNotificationDays",
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
            # ConnectionString intentionally NEVER mapped — credential field.
        },
    ),

    "instance_log": EntitySpec(
        filename="XML_InstanceLog.xml",
        row_tag="Row",
        attribute_map={
            "Id": "Id",
            "InsCompare": "InsCompare",
            "RequestId": "RequestId",
            "FormId": "FormId",
            "DTC": "DTC",
            "FileUploadDT": "FileUploadDT",
            "ReportStartDT": "ReportStartDT",
            "ReportEndDT": "ReportEndDT",
            "ReportingDate": "ReportingDate",
            "Status": "Status",
            "UserId": "UserId",
            "InstanceDocPath": "InstanceDocPath",
            "EncryptDocPath": "EncryptDocPath",
            "ErrorDocPath": "ErrorDocPath",
            "RenderedExcelDocPath": "RenderedExcelDocPath",
            "IsExtract": "IsExtract",
            "IsInstance": "IsInstance",
            "IsCims": "IsCims",
            "IsAudited": "IsAudited",
            "ApprovedBy": "ApprovedBy",
            "ApprovedDt": "ApprovedDt",
            "CIMSUploadBy": "CIMSUploadBy",
            "CIMSUploadDT": "CIMSUploadDT",
            "CIMSUploadStatus": "CIMSUploadStatus",
            "RejectComment": "RejectComment",
            "Comment": "Comment",
        },
    ),

    "nonxbrl_instance_log": EntitySpec(
        filename="XML_NonXBRLInstanceLog.xml",
        row_tag="Row",
        attribute_map={
            "Id": "Id",
            "FormId": "FormId",
            "VersionSelected": "VersionSelected",
            "DTC": "DTC",
            "FileUploadDT": "FileUploadDT",
            "ReportStartDT": "ReportStartDT",
            "ReportEndDT": "ReportEndDT",
            "ReportingDate": "ReportingDate",
            "Status": "Status",
            "UserId": "UserId",
            "InstanceDocPath": "InstanceDocPath",
            "ErrorDocPath": "ErrorDocPath",
            "RenderedDocPath": "RenderedDocPath",
            "IsExtract": "IsExtract",
            "IsInstance": "IsInstance",
            "IsCims": "IsCims",
            "IsAudited": "IsAudited",
            "ApprovedBy": "ApprovedBy",
            "ApprovedDt": "ApprovedDt",
            "CIMSUploadBy": "CIMSUploadBy",
            "CIMSUploadDT": "CIMSUploadDT",
            "CIMSUploadStatus": "CIMSUploadStatus",
            "RejectComment": "RejectComment",
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
