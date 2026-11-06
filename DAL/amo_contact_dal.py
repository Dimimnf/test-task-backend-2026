from models.amo_contact import AmoContact

from DAL.base_dal import BaseDAL


class AmoContactDAL(BaseDAL):
    """DAO для CRM-контактов."""

    model = AmoContact
