# config_6_0.py — 6.0-specific tenant DataBase filenames and attribute mapping.
#
# The 6.0 repo tree (BASE_REPO_PATH/<TenantId>/DataBase/...) mirrors 5.5's folder
# layout (DataBase/, Instance/, Render/) but uses different XML filenames — no
# "XML_" prefix, "Dept" spelled out as "Department", etc. Confirmed against the
# real reference tenant folder (D:\Repo6\Repo6\1001\DataBase):
#
#   5.5 filename          6.0 filename
#   XML_User.xml      ->  User.xml            (same attrs: LoginId, DepartmentId, RoleId)
#   XML_Dept.xml      ->  Department.xml      (forms attr is "ReturnId", not "Forms";
#                                               there is also a separate "NXReturnId"
#                                               for non-XBRL forms — see DEPT_FORMS_ATTR)
#   XML_RoleAccess.xml -> RoleAccess.xml      (OptionId is a numeric ID, not the
#                                               string "CreateInstance" — see
#                                               ROLE_ACCESS_CREATE_INSTANCE_OPTION_ID)
#   XML_InstanceLog.xml -> InstanceLog.xml    (schema differs — see report_lookup.py notes:
#                                               attribute named "ReturnId" here actually
#                                               holds the numeric FormId, not a return code;
#                                               no FormId/UserId/RenderedExcelDocPath attrs)
#   Returns.xml       ->  Return.xml          (Id = FormId, ReturnId = human return code —
#                                               opposite naming from InstanceLog.xml's usage)
#   SchedulerQueue.xml ->  <TenantId>\DataBase\SchedulerQueue.xml — same filename as 5.5,
#                          just tenant-scoped. Auto-created on first schedule request per
#                          tenant (see scheduler_queue_service.append_schedule_entry) — do
#                          not confuse with NxInstanceScheduler.xml, which is a separate,
#                          non-XBRL-only scheduler queue.
#   (new in 6.0)      ->  Period.xml          (repo-relative; 5.5's period.xml is
#                                               project-relative under logs/, not repo-relative
#                                               — see PERIOD_XML_FILENAME)
#   (new in 6.0)      ->  Option.xml          (menu/permission-option registry — maps a
#                                               numeric OptionId, as referenced by
#                                               RoleAccess.xml, to a human-readable Name/
#                                               ResourceId. Used to dynamically resolve which
#                                               OptionId means "Instance Generation" instead of
#                                               hardcoding it — see OPTION_XML_FILENAME below.)
#
# All overridable via env vars in case a different 6.0 deployment differs.

import os

USER_XML_FILENAME: str = os.getenv("XML_6_0_USER_FILENAME", "User.xml")
DEPT_XML_FILENAME: str = os.getenv("XML_6_0_DEPT_FILENAME", "Department.xml")
ROLE_ACCESS_XML_FILENAME: str = os.getenv("XML_6_0_ROLE_ACCESS_FILENAME", "RoleAccess.xml")
INSTANCE_LOG_XML_FILENAME: str = os.getenv("XML_6_0_INSTANCE_LOG_FILENAME", "InstanceLog.xml")
RETURN_XML_FILENAME: str = os.getenv("XML_6_0_RETURN_FILENAME", "Return.xml")
PERIOD_XML_FILENAME: str = os.getenv("XML_6_0_PERIOD_FILENAME", "Period.xml")
OPTION_XML_FILENAME: str = os.getenv("XML_6_0_OPTION_FILENAME", "Option.xml")

# Tenant-scoped scheduler queue file — <TenantId>\DataBase\SchedulerQueue.xml.
# Auto-created (empty <SchedulerQueue /> skeleton) the first time a schedule
# is requested for a tenant that doesn't have one yet — see
# scheduler_queue_service.append_schedule_entry / _create_empty_xml.
SCHEDULER_QUEUE_XML_FILENAME: str = os.getenv("XML_6_0_SCHEDULER_FILENAME", "SchedulerQueue.xml")

# Department.xml's forms attribute — 6.0 splits XBRL vs non-XBRL forms into two
# attributes (ReturnId, NXReturnId) instead of 5.5's single "Forms" attribute.
DEPT_FORMS_ATTR: str = os.getenv("XML_6_0_DEPT_FORMS_ATTR", "ReturnId")
DEPT_NX_FORMS_ATTR: str = os.getenv("XML_6_0_DEPT_NX_FORMS_ATTR", "NXReturnId")

# RoleAccess.xml's OptionId is a numeric ID in 6.0, not the literal string
# "CreateInstance" that 5.5's XML_RoleAccess.xml uses. The numeric ID is NOT
# hardcoded — it's resolved dynamically at lookup time from Option.xml by
# matching RESOURCE_ID_INSTANCE_GENERATION (see auth_service.resolve_option_id_by_resource_id),
# since the same numeric OptionId can differ across deployments/tenants.
#
# Confirmed real data (D:\Repo6\Repo6\1001\DataBase\Option.xml):
#   <Row Id="18" Name="Instance Generation" ResourceId="INSTANCE_GENERATION" .../>
RESOURCE_ID_INSTANCE_GENERATION: str = os.getenv(
    "XML_6_0_RESOURCE_ID_INSTANCE_GENERATION", "INSTANCE_GENERATION"
)

# Manual override — if set, skips the Option.xml lookup and uses this OptionId
# directly. Leave unset (default) so the ResourceId lookup above is authoritative.
ROLE_ACCESS_CREATE_INSTANCE_OPTION_ID: str = os.getenv(
    "XML_6_0_ROLE_ACCESS_CREATE_INSTANCE_OPTION_ID", ""
)

# Option.xml's own id/name/resource attributes.
OPTION_ID_ATTR: str = os.getenv("XML_6_0_OPTION_ID_ATTR", "Id")
OPTION_RESOURCE_ID_ATTR: str = os.getenv("XML_6_0_OPTION_RESOURCE_ID_ATTR", "ResourceId")

# InstanceLog.xml's per-row attribute names differ from 5.5's XML_InstanceLog.xml.
# 5.5 uses: FormId, UserId, InstanceDocPath, RenderedExcelDocPath, ErrorDocPath, Status (label-mapped).
# 6.0 uses:  ReturnId (holds the FormId value, NOT a return code), CreatedBy (email string,
#            not numeric UserId), InstanceDoc, RenderDoc, ErrorDoc, EncryptDoc, Status (numeric enum).
INSTANCE_LOG_FORM_ID_ATTR: str = os.getenv("XML_6_0_INSTANCE_LOG_FORM_ID_ATTR", "ReturnId")
INSTANCE_LOG_CREATED_BY_ATTR: str = os.getenv("XML_6_0_INSTANCE_LOG_CREATED_BY_ATTR", "CreatedBy")
INSTANCE_LOG_INSTANCE_DOC_ATTR: str = os.getenv("XML_6_0_INSTANCE_LOG_INSTANCE_DOC_ATTR", "InstanceDoc")
INSTANCE_LOG_RENDER_DOC_ATTR: str = os.getenv("XML_6_0_INSTANCE_LOG_RENDER_DOC_ATTR", "RenderDoc")
INSTANCE_LOG_ERROR_DOC_ATTR: str = os.getenv("XML_6_0_INSTANCE_LOG_ERROR_DOC_ATTR", "ErrorDoc")

# Return.xml's Id attribute is the numeric FormId (matches Instance/Render folder names).
# Its ReturnId attribute (when present) is the human-readable regulatory return code —
# NOT the same concept as Returns.xml's own Id, and NOT the same attribute name/meaning
# as InstanceLog.xml's "ReturnId" above (which holds a FormId). Do not conflate the two.
RETURN_FORM_ID_ATTR: str = os.getenv("XML_6_0_RETURN_FORM_ID_ATTR", "Id")
RETURN_NAME_ATTR: str = os.getenv("XML_6_0_RETURN_NAME_ATTR", "Name")

# Period.xml's period-id attribute is "Id", not 5.5's "Period_Id". Confirmed:
# 6.0's Period.xml has NO "Frequency" attribute at all (only Id + PeriodName).
# resolve_return_exact() falls back to instance_generator._PERIOD_ID_TO_FREQUENCY
# (a version-stable PeriodId->Frequency table sourced from 5.5's own Period.xml)
# rather than Return.xml's own "RepFreq" attribute directly — RepFreq is
# inconsistent across returns sharing the same PeriodId (e.g. 'A' vs 'Y' both
# appear under PeriodId 107 "Yearly"), which silently broke date-frequency
# validation for any return using an unrecognised RepFreq code.
PERIOD_ID_ATTR: str = os.getenv("XML_6_0_PERIOD_ID_ATTR", "Id")
