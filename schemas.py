from typing import Dict, List, Optional

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, RootModel


class BalanceHeadTable(BaseModel):
    organization: Optional[str] = Field(
        None, alias="Организация", description="Название организации"
    )
    taxpayer_id: Optional[int] = Field(
        None, alias="Учетный номер плательщика", description="Учетный номер плательщика"
    )
    economic_activity: Optional[str] = Field(
        None,
        alias="Вид экономической деятельности",
        description="Вид экономической деятельности",
    )
    legal_form: Optional[str] = Field(
        None,
        alias="Организационно-правовая форма",
        description="Организационно-правовая форма",
    )
    governing_body: Optional[str] = Field(
        None, alias="Орган управления", description="Орган управления"
    )
    unit: Optional[str] = Field(
        None, alias="Единица измерения", description="Единица измерения"
    )
    address: Optional[str] = Field(None, alias="Адрес", description="Адрес")


class BalanceDatesTable(BaseModel):
    approval_date: Optional[str] = Field(
        None,
        alias="Дата утверждения",
        description="Дата утверждения в формате ДД.ММ.ГГГГ",
    )
    submission_date: Optional[str] = Field(
        None, alias="Дата отправки", description="Дата отправки в формате ДД.ММ.ГГГГ"
    )
    acceptance_date: Optional[str] = Field(
        None, alias="Дата принятия", description="Дата принятия в формате ДД.ММ.ГГГГ"
    )


class BalanceMainTable(RootModel):
    root: Dict[str, List[Optional[int]]]


class ReportMainTable(RootModel):
    root: Dict[str, List[Optional[int]]]


class TablesData(BaseModel):
    balance_head_table: BalanceHeadTable
    balance_dates_table: BalanceDatesTable
    balance_main_table_dates: List[Optional[str]] = Field(
        ...,
        description="Даты, соответствующие двум столбцам основной таблицы баланса в формате ДД.ММ.ГГГГ",
    )
    balance_main_table: BalanceMainTable
    report_main_table: ReportMainTable


class ParsedPDF(BaseModel):
    tables_data: TablesData


parser = PydanticOutputParser(pydantic_object=ParsedPDF)
