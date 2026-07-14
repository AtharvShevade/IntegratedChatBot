"""iDEAL 6.0 entity schema — translates 6.0's raw attribute names onto the
same 5.5-canonical logical field names used throughout query_handlers.py.

All filenames/attribute names below are confirmed directly against real
tenant data at D:\\Repo6\\Repo6\\1001\\DataBase (2026-07-13). Do not guess —
if a 6.0 concept genuinely doesn't exist, the entity is either omitted
(load_entity then returns [] gracefully) or mapped to None fields, and
that gap is called out in the comment.

CONFIRMED ABSENT IN 6.0 (verified by exhaustive directory listing of
tenant 1001 — no filename resembling these exists at all):
  - segments      (no Segment.xml equivalent)
  - error_log     (no ErrorLog.xml equivalent)
  - uploaded_file_log   (no UploadedFileLog.xml equivalent)
  - cross_validation_log (no CrossValidationLog.xml equivalent)
These 4 entities are OMITTED from this schema. XMLStore/loader.load_entity
returns [] for them under 6.0 (entity_name not in schema -> warning + []),
which callers already handle as "no data" rather than an error.
"""
from __future__ import annotations

from backend.db_qa.versions.loader import EntitySpec

SCHEMA: dict[str, EntitySpec] = {

    "users": EntitySpec(
        filename="User.xml",
        row_tag="Row",
        attribute_map={
            "UserId": "Id",
            "Name": "FirstName",  # NOTE: ciphertext in 6.0 — see templates._display_value
            "EmailId": "EmailId",  # ciphertext in 6.0
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
            "MobileNumber": "PhoneNumber",  # ciphertext in 6.0
            "CreatedBy": "ActionBy",  # 6.0 has no separate CreatedBy attr
            "UserCreationDate": "ActionDate",  # best-available proxy, no dedicated attr
            # Password, SecondPassword..FifthPassword, Answer, RefreshToken,
            # RefreshTokenExpiryTime are intentionally NEVER mapped here.
        },
        json_fallback=True,
        json_filename="User.json",
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
            "Level1UserEmails": "Level1UserEmails",
            "Level2UserEmails": "Level2UserEmails",
            "Level3UserEmails": "Level3UserEmails",
        },
        json_fallback=True,
        json_filename="Department.json",
    ),

    "roles": EntitySpec(
        filename="Role.xml",
        row_tag="Row",
        attribute_map={
            "RoleId": "Id",
            "Name": "Name",
            "Status": "Status",
        },
        json_fallback=True,
        json_filename="Role.json",
    ),

    "role_access": EntitySpec(
        filename="RoleAccess.xml",
        row_tag="Row",
        attribute_map={
            "OptionId": "OptionId",  # numeric in 6.0 — resolve via options/ResourceId
            "RoleId": "RoleId",
            "HasNew": "HasNew",
            "HasEdit": "HasEdit",
            "HasView": "HasView",
            "HasApprove": "HasApprove",
        },
        json_fallback=True,
        json_filename="RoleAccess.json",
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
            "RepFreq": "RepFreq",  # used as the Period.Frequency fallback
            "IsCims": "IsCims",
            "IsTBL": "IsTBL",
            "IsExcel": "IsExcel",
            "ReturnId": "ReturnId",
            "AltName": "AltName",
            "DueDays": "DueDays",
        },
        json_fallback=True,
        json_filename="Return.json",
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
            "ReturnId": "ReturnId",
            "JobProcessingId": "JobProcessingId",
            "IsCims": "IsCims",
            "HasFolder": "HasFolder",
        },
        json_fallback=True,
        json_filename="NonXBRLReturn.json",
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
            "IsMenu": "Status",  # 6.0 has no dedicated IsMenu attr; Status is closest proxy
            "ResourceId": "ResourceId",
            "CanNew": "CanNew",
            "CanEdit": "CanEdit",
            "CanView": "CanView",
            "CanApprove": "CanApprove",
        },
        json_fallback=True,
        json_filename="Option.json",
    ),

    "periods": EntitySpec(
        filename="Period.xml",
        row_tag="Row",
        attribute_map={
            "Period_Id": "Id",
            # CONFIRMED: 6.0 Period.xml has NO Frequency attribute at all.
            # Keep the logical key present (value None) for column parity;
            # callers fall back to the return's own RepFreq attribute —
            # see XMLStore.frequency_for_return().
            "Frequency": "Frequency",
            "EBRFrequency": "EBRFrequency",
            "PeriodName": "PeriodName",
            "AdvanceNotificationDays": "AdvanceNotificationDays",
        },
    ),

    "providers": EntitySpec(
        filename="Provider.xml",
        row_tag="Row",
        attribute_map={
            "ProviderId": "Id",
            "ProviderName": "Name",
            "ProviderType": "ProviderType",
            "IsActive": "Status",
            # ConnectionString intentionally NEVER mapped — credential field.
        },
    ),

    "instance_log": EntitySpec(
        filename="InstanceLog.xml",
        row_tag="Row",
        attribute_map={
            "Id": "Id",
            "InsCompare": "AuditFilterValue",  # closest 6.0 proxy; semantics differ, do not over-trust
            "RequestId": "Id",  # 6.0 has no separate RequestId; reuses Id
            "FormId": "ReturnId",  # NOTE: holds the numeric FormId, NOT a return code (config_6_0.py)
            "DTC": "CreateDT",
            "FileUploadDT": "CreateDT",  # no dedicated FileUploadDT in 6.0
            "ReportStartDT": "ReportStartDT",
            "ReportEndDT": "ReportEndDT",
            "ReportingDate": "ReportingDate",
            "Status": "Status",  # NOTE: different numeric scale than 5.5 (e.g. 30/70) — do not reuse SUBMISSION_STATUS_LABELS as-is
            "UserId": "CreatedBy",  # holds an email string, not numeric UserId
            "InstanceDocPath": "InstanceDoc",
            "EncryptDocPath": "EncryptDoc",
            "ErrorDocPath": "ErrorDoc",
            "RenderedExcelDocPath": "RenderDoc",
            "IsExtract": "IsExtract",
            "IsInstance": "IsInstance",
            "IsCims": "IsExtract",  # no dedicated IsCims attr in 6.0; placeholder proxy, revisit
            "IsAudited": "Status",  # no dedicated IsAudited attr; derive from Status if needed
            "ApprovedBy": "ApprovedBy",
            "ApprovedDt": "ApprovedDT",
            "CIMSUploadBy": "SubmitBy",
            "CIMSUploadDT": "SubmitDT",
            "CIMSUploadStatus": "SourceType",  # no dedicated attr; placeholder proxy, revisit
            "RejectComment": "Comment",
            "Comment": "Comment",
        },
    ),

    "nonxbrl_instance_log": EntitySpec(
        filename="NxInstanceLog.xml",
        row_tag="Row",
        attribute_map={
            "Id": "Id",
            "FormId": "ReturnId",
            "VersionSelected": "Version",
            "DTC": "CreateDT",
            "FileUploadDT": "CreateDT",
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
            "IsCims": "IsExtract",  # placeholder proxy, revisit
            "IsAudited": "Status",  # placeholder proxy, revisit
            "ApprovedBy": "ApprovedBy",
            "ApprovedDt": "ApprovedDT",
            "CIMSUploadBy": "SubmitBy",
            "CIMSUploadDT": "SubmitDT",
            "CIMSUploadStatus": None,  # not applicable — see loader note below
            "RejectComment": "Comment",
            "Comment": "Comment",
        },
    ),

    "audit": EntitySpec(
        filename="AuditLog.xml",
        row_tag="Row",
        attribute_map={
            # 6.0's AuditLog.xml has a materially different schema than 5.5's
            # XML_Audit.xml (no OptionId; has ModuleName/ActionType/ActionDetails
            # instead). Mapped onto the closest 5.5-shaped logical fields;
            # OptionId/VersionSelected have no 6.0 equivalent (None).
            "OptionId": None,
            "AuditDateTime": "DTC",
            "AuditType": "ActionType",
            "UserId": "ActionBy",
            "Remark": "Comment",
            "VersionSelected": None,
        },
        json_fallback=True,
        json_filename="AuditLog.json",
    ),

    "bank_details": EntitySpec(
        filename="XML_BankDetail.xml",  # confirmed: 6.0 keeps the 5.5 filename verbatim
        row_tag="Row",
        attribute_map={
            "BankCode": "BankCode",
            "BankName": "BankName",
            "BankType": "BankType",
            "CRR": "CRR",
        },
    ),

    # segments, error_log, uploaded_file_log, cross_validation_log:
    # CONFIRMED ABSENT in 6.0 (see module docstring) — intentionally omitted.
}
