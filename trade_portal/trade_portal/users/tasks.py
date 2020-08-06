import logging

from constance import config
from django.conf import settings
from config import celery_app
from templated_email import send_templated_mail

from trade_portal.legi.abr import fetch_abn_info
from trade_portal.users.models import User, Organisation, OrgRoleRequest


logger = logging.getLogger(__name__)


def custom_template_email(*args, **kwargs):
    """
    Just some default parameters set for our use-case
    """
    kwargs.update({
        "from_email": settings.DEFAULT_FROM_EMAIL,
        "fail_silently": True,
    })
    kwargs["context"]["HOST"] = settings.ICL_TRADE_PORTAL_HOST
    return send_templated_mail(
        *args, **kwargs
    )


@celery_app.task(ignore_result=True,
                 max_retries=3, interval_start=10, interval_step=10, interval_max=50)
def update_org_fields(org_id):
    """
    For freshly created org
    Makes a request to a business register (if supported for that country)
    And fills the organisation name and other fields
    """
    org = Organisation.objects.get(pk=org_id)

    if settings.ICL_APP_COUNTRY == "AU":
        try:
            abn_info = fetch_abn_info(org.business_id)
        except Exception as e:
            logger.exception(e)
        else:
            business_name = abn_info.get("EntityName") or ""
            entity_code = abn_info.get("EntityTypeCode") or "org"
            if business_name:
                org.name = business_name
                org.dot_separated_id = f"{org.business_id}.{entity_code}.{settings.BID_NAME}"
                org.save()
                logger.info("Organisation %s name has been updated", org)
    return


@celery_app.task(ignore_result=True)
def notify_about_new_user_created(user_id):
    user = User.objects.get(pk=user_id)

    if not config.USERS_NOTIFICATIONS_MAILBOX:
        logger.warning(
            "USERS_NOTIFICATIONS_MAILBOX is not configured - ignoring the email message"
        )
        return

    custom_template_email(
        template_name='user_created_to_staff',
        recipient_list=[config.USERS_NOTIFICATIONS_MAILBOX],
        context={'user': user},
    )


@celery_app.task(ignore_result=True)
def notify_user_about_being_approved(user_id, action_taken):
    """
    When superuser either creates the organisation for this user or add
    to an existing one
    """
    user = User.objects.get(pk=user_id)

    custom_template_email(
        template_name='user_approved_to_user',
        recipient_list=[user.email],
        context={'user': user},
    )


@celery_app.task(ignore_result=True)
def notify_role_requested(request_id):
    req = OrgRoleRequest.objects.get(pk=request_id)

    if not config.USERS_NOTIFICATIONS_MAILBOX:
        logger.warning(
            "USERS_NOTIFICATIONS_MAILBOX is not configured - ignoring the email message"
        )
        return

    custom_template_email(
        template_name='role_requested_to_staff',
        recipient_list=[config.USERS_NOTIFICATIONS_MAILBOX],
        context={'req': req},
    )


@celery_app.task(ignore_result=True)
def notify_user_about_role_request_changed(req_id):
    """
    When superuser either creates the organisation for this user or add
    to an existing one
    """
    req = OrgRoleRequest.objects.get(pk=req_id)

    custom_template_email(
        template_name='role_request_changed_to_user',
        recipient_list=[req.created_by.email],
        context={'req': req},
    )


@celery_app.task(ignore_result=True)
def notify_staff_about_evidence_uploaded(req_id):
    """
    When user uploads an evidence to a request in "evidence" status
    """
    req = OrgRoleRequest.objects.get(pk=req_id)

    if not config.USERS_NOTIFICATIONS_MAILBOX:
        logger.warning(
            "USERS_NOTIFICATIONS_MAILBOX is not configured - ignoring the email message"
        )
        return

    custom_template_email(
        template_name='evidence_uploaded_to_staff',
        recipient_list=[config.USERS_NOTIFICATIONS_MAILBOX],
        context={'req': req},
    )
