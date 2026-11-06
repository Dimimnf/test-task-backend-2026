from models.amo_company import AmoCompany

from DAL.base_dal import BaseDAL


class AmoCompanyDAL(BaseDAL):
    """DAO для CRM-компаний."""

    model = AmoCompany
