from sqlalchemy import Numeric, BigInteger
from src.models.base import Base
from src.models.financial._mixins import FinancialBaseMixin
from sqlalchemy.orm import Mapped, mapped_column


class FinancialPerShare(FinancialBaseMixin, Base):
    __tablename__ = "financial_per_share"

    eps: Mapped[float | None] = mapped_column(Numeric(10, 4))
    deduct_eps: Mapped[float | None] = mapped_column(Numeric(10, 4))
    retained_ps: Mapped[float | None] = mapped_column(Numeric(10, 4))
    bps: Mapped[float | None] = mapped_column(Numeric(10, 4))
    capital_reserve_ps: Mapped[float | None] = mapped_column(Numeric(10, 4))
    roe_ps: Mapped[float | None] = mapped_column(Numeric(10, 4))
    op_cf_ps: Mapped[float | None] = mapped_column(Numeric(10, 4))
    weight_roe: Mapped[float | None] = mapped_column("weighted_roe", Numeric(10, 4))
    deduct_ps: Mapped[float | None] = mapped_column(Numeric(10, 4))
    sq_eps: Mapped[float | None] = mapped_column(Numeric(10, 4))
    sq_total_revenue: Mapped[float | None] = mapped_column(Numeric(20, 2))
    ent_fcf_ps: Mapped[float | None] = mapped_column(Numeric(10, 4))
    eq_fcf_ps: Mapped[float | None] = mapped_column(Numeric(10, 4))
    sq_revenue: Mapped[float | None] = mapped_column(Numeric(20, 2))
    sq_op_profit: Mapped[float | None] = mapped_column(Numeric(20, 2))
    sq_parent_net_profit: Mapped[float | None] = mapped_column(Numeric(20, 2))
    sq_deduct_profit: Mapped[float | None] = mapped_column(Numeric(20, 2))
    sq_op_cf: Mapped[float | None] = mapped_column(Numeric(20, 2))
    sq_inv_cf: Mapped[float | None] = mapped_column(Numeric(20, 2))
    sq_fin_cf: Mapped[float | None] = mapped_column(Numeric(20, 2))
    sq_cash_change: Mapped[float | None] = mapped_column(Numeric(20, 2))
    cf_ps: Mapped[float | None] = mapped_column(Numeric(10, 4))
