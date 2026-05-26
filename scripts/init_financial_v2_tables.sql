CREATE TABLE IF NOT EXISTS financial_balance_sheet (
    symbol              TEXT NOT NULL,
    report_date         DATE NOT NULL,

    -- 【流动资产 Current Assets】
    monetary_fund               NUMERIC(20,2),  -- 货币资金(ID=8)
    trading_asset               NUMERIC(20,2),  -- 交易性金融资产(ID=9)
    notes_receivable            NUMERIC(20,2),  -- 应收票据(ID=10)
    accounts_receivable         NUMERIC(20,2),  -- 应收账款(ID=11)
    prepayment                  NUMERIC(20,2),  -- 预付款项(ID=12)
    other_receivable            NUMERIC(20,2),  -- 其他应收款(ID=13)
    related_party_receivable    NUMERIC(20,2),  -- 应收关联公司款(ID=14)
    interest_receivable         NUMERIC(20,2),  -- 应收利息(ID=15)
    dividend_receivable         NUMERIC(20,2),  -- 应收股利(ID=16)
    inventory                   NUMERIC(20,2),  -- 存货(ID=17)
    biological_asset            NUMERIC(20,2),  -- 消耗性生物资产(ID=18)
    non_current_asset_1y        NUMERIC(20,2),  -- 一年内到期的非流动资产(ID=19)
    other_current_asset         NUMERIC(20,2),  -- 其他流动资产(ID=20)
    current_assets_total        NUMERIC(20,2),  -- 流动资产合计(ID=21)

    -- 【非流动资产 Non-Current Assets】
    available_for_sale_asset        NUMERIC(20,2),  -- 可供出售金融资产(ID=22)
    held_to_maturity_invest         NUMERIC(20,2),  -- 持有至到期投资(ID=23)
    long_term_receivable            NUMERIC(20,2),  -- 长期应收款(ID=24)
    long_term_equity_invest         NUMERIC(20,2),  -- 长期股权投资(ID=25)
    investment_property             NUMERIC(20,2),  -- 投资性房地产(ID=26)
    fixed_asset                     NUMERIC(20,2),  -- 固定资产(ID=27)
    construction_in_progress        NUMERIC(20,2),  -- 在建工程(ID=28)
    engineering_material            NUMERIC(20,2),  -- 工程物资(ID=29)
    fixed_asset_clearance           NUMERIC(20,2),  -- 固定资产清理(ID=30)
    productive_biological_asset     NUMERIC(20,2),  -- 生产性生物资产(ID=31)
    oil_gas_asset                   NUMERIC(20,2),  -- 油气资产(ID=32)
    intangible_asset                NUMERIC(20,2),  -- 无形资产(ID=33)
    development_expenditure         NUMERIC(20,2),  -- 开发支出(ID=34)
    goodwill                        NUMERIC(20,2),  -- 商誉(ID=35)
    long_term_deferred_exp          NUMERIC(20,2),  -- 长期待摊费用(ID=36)
    deferred_tax_asset              NUMERIC(20,2),  -- 递延所得税资产(ID=37)
    other_non_current_asset         NUMERIC(20,2),  -- 其他非流动资产(ID=38)
    non_current_assets_total        NUMERIC(20,2),  -- 非流动资产合计(ID=39)

    assets_total                 NUMERIC(20,2),  -- 资产总计(ID=40)

    -- 【流动负债 Current Liabilities】
    short_term_borrowing         NUMERIC(20,2),  -- 短期借款(ID=41)
    trading_liability            NUMERIC(20,2),  -- 交易性金融负债(ID=42)
    notes_payable                NUMERIC(20,2),  -- 应付票据(ID=43)
    accounts_payable             NUMERIC(20,2),  -- 应付账款(ID=44)
    advance_from_customers       NUMERIC(20,2),  -- 预收款项(ID=45)
    employee_payable             NUMERIC(20,2),  -- 应付职工薪酬(ID=46)
    taxes_payable                NUMERIC(20,2),  -- 应交税费(ID=47)
    interest_payable             NUMERIC(20,2),  -- 应付利息(ID=48)
    dividend_payable             NUMERIC(20,2),  -- 应付股利(ID=49)
    other_payable                NUMERIC(20,2),  -- 其他应付款(ID=50)
    related_party_payable        NUMERIC(20,2),  -- 应付关联公司款(ID=51)
    non_current_liab_1y          NUMERIC(20,2),  -- 一年内到期的非流动负债(ID=52)
    other_current_liab           NUMERIC(20,2),  -- 其他流动负债(ID=53)
    current_liab_total           NUMERIC(20,2),  -- 流动负债合计(ID=54)

    -- 【非流动负债 Non-Current Liabilities】
    long_term_borrowing          NUMERIC(20,2),  -- 长期借款(ID=55)
    bonds_payable                NUMERIC(20,2),  -- 应付债券(ID=56)
    long_term_payable            NUMERIC(20,2),  -- 长期应付款(ID=57)
    specific_payable             NUMERIC(20,2),  -- 专项应付款(ID=58)
    provisions                   NUMERIC(20,2),  -- 预计负债(ID=59)
    deferred_tax_liab            NUMERIC(20,2),  -- 递延所得税负债(ID=60)
    other_non_current_liab       NUMERIC(20,2),  -- 其他非流动负债(ID=61)
    non_current_liab_total       NUMERIC(20,2),  -- 非流动负债合计(ID=62)

    liabilities_total            NUMERIC(20,2),  -- 负债合计(ID=63)

    -- 【所有者权益 Owners' Equity】
    share_capital                NUMERIC(20,2),  -- 实收资本（股本）(ID=64)
    capital_reserve              NUMERIC(20,2),  -- 资本公积(ID=65)
    surplus_reserve              NUMERIC(20,2),  -- 盈余公积(ID=66)
    treasury_share               NUMERIC(20,2),  -- 库存股(ID=67)
    retained_earnings            NUMERIC(20,2),  -- 未分配利润(ID=68)
    minority_interest            NUMERIC(20,2),  -- 少数股东权益(ID=69)
    fx_translation_diff          NUMERIC(20,2),  -- 外币报表折算价差(ID=70)
    abnormal_item_adjust         NUMERIC(20,2),  -- 非正常经营项目收益调整(ID=71)
    equity_total                 NUMERIC(20,2),  -- 所有者权益合计(ID=72)

    liab_and_equity_total        NUMERIC(20,2),  -- 负债和所有者权益合计(ID=73)

    -- 【补充指标 Extended BS Items】
    notes_and_receivable_sum        NUMERIC(20,2),  -- 应收票据及应收账款(ID=296)
    notes_and_payable_sum           NUMERIC(20,2),  -- 应付票据及应付账款(ID=295)
    deferred_revenue                NUMERIC(20,2),  -- 递延收益(ID=297)
    other_comprehensive_income      NUMERIC(20,2),  -- 其他综合收益(资产负债)(ID=298)
    other_equity_instrument         NUMERIC(20,2),  -- 其他权益工具(ID=299)
    parent_equity_excl_minority     NUMERIC(20,2),  -- 归属于母公司股东权益(ID=271)

    -- 【新资产负债表 New BS (401-439)】
    special_reserve                 NUMERIC(20,2),  -- 专项储备(ID=401, 万元)
    settlement_provision            NUMERIC(20,2),  -- 结算备付金(ID=402, 万元)
    lending_fund                    NUMERIC(20,2),  -- 拆出资金(ID=403, 万元)
    loan_advance_ca                 NUMERIC(20,2),  -- 发放贷款及垫款(流动资产)(ID=404, 万元)
    derivative_asset                NUMERIC(20,2),  -- 衍生金融资产(ID=405, 万元)
    premium_receivable              NUMERIC(20,2),  -- 应收保费(ID=406, 万元)
    reinsurance_receivable          NUMERIC(20,2),  -- 应收分保账款(ID=407, 万元)
    reinsurance_reserve_receiv      NUMERIC(20,2),  -- 应收分保合同准备金(ID=408, 万元)
    resale_agreement_asset          NUMERIC(20,2),  -- 买入返售金融资产(ID=409, 万元)
    asset_held_for_sale             NUMERIC(20,2),  -- 划分为持有待售的资产(ID=410, 万元)
    loan_advance_nca                NUMERIC(20,2),  -- 发放贷款及垫款(非流动资产)(ID=411, 万元)

    central_bank_borrowing          NUMERIC(20,2),  -- 向中央银行借款(ID=412, 万元)
    deposit_interbank               NUMERIC(20,2),  -- 吸收存款及同业存放(ID=413, 万元)
    borrowing_from_fi               NUMERIC(20,2),  -- 拆入资金(ID=414, 万元)
    derivative_liab                 NUMERIC(20,2),  -- 衍生金融负债(ID=415, 万元)
    repo_liability                  NUMERIC(20,2),  -- 卖出回购金融资产款(ID=416, 万元)
    commission_payable              NUMERIC(20,2),  -- 应付手续费及佣金(ID=417, 万元)
    reinsurance_payable             NUMERIC(20,2),  -- 应付分保账款(ID=418, 万元)
    insurance_reserve               NUMERIC(20,2),  -- 保险合同准备金(ID=419, 万元)
    brokerage_agent_fund            NUMERIC(20,2),  -- 代理买卖证券款(ID=420, 万元)
    underwriting_agent_fund         NUMERIC(20,2),  -- 代理承销证券款(ID=421, 万元)
    liab_held_for_sale              NUMERIC(20,2),  -- 划分为持有待售的负债(ID=422, 万元)
    provisions_new                  NUMERIC(20,2),  -- 预计负债(新)(ID=423, 万元)
    deferred_revenue_current        NUMERIC(20,2),  -- 递延收益(流动负债)(ID=424, 万元)
    preferred_stock_ncl             NUMERIC(20,2),  -- 优先股(非流动负债)(ID=425, 万元)
    perpetual_bond_ncl              NUMERIC(20,2),  -- 永续债(非流动负债)(ID=426, 万元)
    long_term_employee_payable      NUMERIC(20,2),  -- 长期应付职工薪酬(ID=427, 万元)
    preferred_stock_eq              NUMERIC(20,2),  -- 优先股(所有者权益)(ID=428, 万元)
    perpetual_bond_eq               NUMERIC(20,2),  -- 永续债(所有者权益)(ID=429, 万元)
    debt_investment                 NUMERIC(20,2),  -- 债权投资(ID=430, 万元)
    other_debt_investment           NUMERIC(20,2),  -- 其他债权投资(ID=431, 万元)
    other_equity_investment         NUMERIC(20,2),  -- 其他权益工具投资(ID=432, 万元)
    other_non_curr_fin_asset        NUMERIC(20,2),  -- 其他非流动金融资产(ID=433, 万元)
    contract_liability              NUMERIC(20,2),  -- 合同负债(ID=434, 万元)
    contract_asset                  NUMERIC(20,2),  -- 合同资产(ID=435, 万元)
    other_asset                     NUMERIC(20,2),  -- 其他资产(ID=436, 万元)
    receivable_financing            NUMERIC(20,2),  -- 应收款项融资(ID=437, 万元)
    right_of_use_asset              NUMERIC(20,2),  -- 使用权资产(ID=438, 万元)
    lease_liability                 NUMERIC(20,2),  -- 租赁负债(ID=439, 万元)

    source     TEXT NOT NULL DEFAULT 'mootdx',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, report_date)
);

CREATE TABLE IF NOT EXISTS financial_income_sheet (
    symbol      TEXT NOT NULL,
    report_date DATE NOT NULL,

    revenue                 NUMERIC(20,2),  -- 营业收入(ID=74)
    cost_of_sales           NUMERIC(20,2),  -- 营业成本(ID=75)
    biz_tax_surcharge       NUMERIC(20,2),  -- 营业税金及附加(ID=76)
    selling_expense         NUMERIC(20,2),  -- 销售费用(ID=77)
    admin_expense           NUMERIC(20,2),  -- 管理费用(ID=78)
    exploration_expense     NUMERIC(20,2),  -- 勘探费用(ID=79)
    finance_expense         NUMERIC(20,2),  -- 财务费用(ID=80)
    asset_impairment        NUMERIC(20,2),  -- 资产减值损失(ID=81)
    fv_gain                 NUMERIC(20,2),  -- 公允价值变动净收益(ID=82)
    invest_income           NUMERIC(20,2),  -- 投资收益(ID=83)
    invest_income_ae        NUMERIC(20,2),  -- 对联营合营企业投资收益(ID=84)
    other_pnl_adj           NUMERIC(20,2),  -- 影响营业利润的其他科目(ID=85)
    operating_profit        NUMERIC(20,2),  -- 营业利润(ID=86)
    subsidy_income          NUMERIC(20,2),  -- 补贴收入(ID=87)
    non_op_income           NUMERIC(20,2),  -- 营业外收入(ID=88)
    non_op_expense          NUMERIC(20,2),  -- 营业外支出(ID=89)
    nca_disposal_loss       NUMERIC(20,2),  -- 非流动资产处置净损失(ID=90)
    other_pnl_adj_sub       NUMERIC(20,2),  -- 影响利润总额的其他科目(ID=91)
    profit_total            NUMERIC(20,2),  -- 利润总额(ID=92)
    income_tax              NUMERIC(20,2),  -- 所得税(ID=93)
    other_net_pnl_adj       NUMERIC(20,2),  -- 影响净利润的其他科目(ID=94)
    net_profit              NUMERIC(20,2),  -- 净利润(ID=95)
    parent_net_profit       NUMERIC(20,2),  -- 归属于母公司净利润(ID=96)
    minority_pnl            NUMERIC(20,2),  -- 少数股东损益(ID=97)

    -- 【补充指标】
    other_comprehensive_pnl     NUMERIC(20,2),  -- 其他综合收益(利润表)(ID=269)
    comprehensive_income        NUMERIC(20,2),  -- 综合收益总额(ID=270)

    other_income                NUMERIC(20,2),  -- 其他收益(ID=300)
    asset_disposal_gain         NUMERIC(20,2),  -- 资产处置收益(ID=301)
    continuing_op_net_profit    NUMERIC(20,2),  -- 持续经营净利润(ID=302)
    discontinued_op_net_pnl     NUMERIC(20,2),  -- 终止经营净利润(ID=303)
    rd_expense                  NUMERIC(20,2),  -- 研发费用(ID=304)
    interest_expense_fin        NUMERIC(20,2),  -- 利息费用(ID=305)
    interest_income_fin         NUMERIC(20,2),  -- 利息收入(ID=306)

    -- 【新利润表 New IS (501-521)】
    diluted_eps                 NUMERIC(10,4),  -- 稀释每股收益(ID=501, 元)
    total_revenue               NUMERIC(20,2),  -- 营业总收入(ID=502, 万元)
    exchange_gain               NUMERIC(20,2),  -- 汇兑收益(ID=503, 万元)
    parent_comprehensive        NUMERIC(20,2),  -- 归属于母公司综合收益(ID=504, 万元)
    minority_comprehensive      NUMERIC(20,2),  -- 归属于少数股东综合收益(ID=505, 万元)
    interest_income_is          NUMERIC(20,2),  -- 利息收入(新)(ID=506, 万元)
    earned_premium              NUMERIC(20,2),  -- 已赚保费(ID=507, 万元)
    fee_commission_income       NUMERIC(20,2),  -- 手续费及佣金收入(ID=508, 万元)
    interest_expense_is         NUMERIC(20,2),  -- 利息支出(新)(ID=509, 万元)
    fee_commission_expense      NUMERIC(20,2),  -- 手续费及佣金支出(ID=510, 万元)
    surrender_payment           NUMERIC(20,2),  -- 退保金(ID=511, 万元)
    claim_payout                NUMERIC(20,2),  -- 赔付支出净额(ID=512, 万元)
    insurance_reserve_withdraw  NUMERIC(20,2),  -- 提取保险合同准备金净额(ID=513, 万元)
    policy_dividend             NUMERIC(20,2),  -- 保单红利支出(ID=514, 万元)
    reinsurance_expense         NUMERIC(20,2),  -- 分保费用(ID=515, 万元)
    nca_disposal_gain_new       NUMERIC(20,2),  -- 非流动资产处置利得(ID=516, 万元)
    credit_impairment           NUMERIC(20,2),  -- 信用减值损失(ID=517, 万元)
    net_hedge_gain              NUMERIC(20,2),  -- 净敞口套期收益(ID=518, 万元)
    total_op_cost               NUMERIC(20,2),  -- 营业总成本(ID=519, 万元)
    credit_impairment_2019      NUMERIC(20,2),  -- 信用减值损失(2019格式)(ID=520, 万元)
    asset_impairment_2019       NUMERIC(20,2),  -- 资产减值损失(2019格式)(ID=521, 万元)

    source     TEXT NOT NULL DEFAULT 'mootdx',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, report_date)
);

CREATE TABLE IF NOT EXISTS financial_cash_flow (
    symbol      TEXT NOT NULL,
    report_date DATE NOT NULL,

    -- 【经营活动 Operating】
    sale_receipt                    NUMERIC(20,2),  -- 销售商品收到的现金(ID=98)
    tax_refund                      NUMERIC(20,2),  -- 收到的税费返还(ID=99)
    other_op_cash_in                NUMERIC(20,2),  -- 收到其他经营现金(ID=100)
    op_cash_inflow                  NUMERIC(20,2),  -- 经营活动现金流入小计(ID=101)
    goods_purchase_payment          NUMERIC(20,2),  -- 购买商品支付现金(ID=102)
    employee_payment                NUMERIC(20,2),  -- 支付职工现金(ID=103)
    tax_payment                     NUMERIC(20,2),  -- 支付的各项税费(ID=104)
    other_op_cash_out               NUMERIC(20,2),  -- 支付其他经营现金(ID=105)
    op_cash_outflow                 NUMERIC(20,2),  -- 经营活动现金流出小计(ID=106)
    op_net_cash_flow                NUMERIC(20,2),  -- 经营净现金流(ID=107)

    -- 【投资活动 Investing】
    invest_withdrawal               NUMERIC(20,2),  -- 收回投资收到的现金(ID=108)
    invest_income_receipt           NUMERIC(20,2),  -- 取得投资收益收到的现金(ID=109)
    nca_disposal_receipt            NUMERIC(20,2),  -- 处置固定资产收回现金(ID=110)
    subsidiary_disposal_receipt     NUMERIC(20,2),  -- 处置子公司收回现金(ID=111)
    other_inv_cash_in               NUMERIC(20,2),  -- 收到其他投资现金(ID=112)
    inv_cash_inflow                 NUMERIC(20,2),  -- 投资活动现金流入小计(ID=113)
    nca_purchase_payment            NUMERIC(20,2),  -- 购建固定资产支付现金(ID=114)
    invest_payment                  NUMERIC(20,2),  -- 投资支付的现金(ID=115)
    subsidiary_acquisition_pay      NUMERIC(20,2),  -- 取得子公司支付现金(ID=116)
    other_inv_cash_out              NUMERIC(20,2),  -- 支付其他投资现金(ID=117)
    inv_cash_outflow                NUMERIC(20,2),  -- 投资活动现金流出小计(ID=118)
    inv_net_cash_flow               NUMERIC(20,2),  -- 投资净现金流(ID=119)

    -- 【筹资活动 Financing】
    capital_contribution_receipt    NUMERIC(20,2),  -- 吸收投资收到的现金(ID=120)
    borrowing_receipt               NUMERIC(20,2),  -- 取得借款收到的现金(ID=121)
    other_fin_cash_in               NUMERIC(20,2),  -- 收到其他筹资现金(ID=122)
    fin_cash_inflow                 NUMERIC(20,2),  -- 筹资活动现金流入小计(ID=123)
    debt_repayment                  NUMERIC(20,2),  -- 偿还债务支付的现金(ID=124)
    dividend_interest_payment       NUMERIC(20,2),  -- 分配股利利润偿付利息(ID=125)
    other_fin_cash_out              NUMERIC(20,2),  -- 支付其他筹资现金(ID=126)
    fin_cash_outflow                NUMERIC(20,2),  -- 筹资活动现金流出小计(ID=127)
    fin_net_cash_flow               NUMERIC(20,2),  -- 筹资净现金流(ID=128)

    -- 【汇率及其他】
    fx_effect                       NUMERIC(20,2),  -- 汇率变动对现金的影响(ID=129)
    other_cash_effect               NUMERIC(20,2),  -- 其他原因对现金的影响(ID=130)
    cash_net_increase               NUMERIC(20,2),  -- 现金净增加额(ID=131)
    cash_begin_balance              NUMERIC(20,2),  -- 期初现金余额(ID=132)
    cash_end_balance                NUMERIC(20,2),  -- 期末现金余额(ID=133)

    -- 【间接法 - 经营净现金流补充 Indirect Method】
    net_profit_cf                   NUMERIC(20,2),  -- 净利润(间接法)(ID=134)
    asset_impairment_provision      NUMERIC(20,2),  -- 资产减值准备(ID=135)
    depreciation_amortization       NUMERIC(20,2),  -- 折旧摊销(ID=136)
    intangible_amortization         NUMERIC(20,2),  -- 无形资产摊销(ID=137)
    deferred_expense_amort          NUMERIC(20,2),  -- 长期待摊费用摊销(ID=138)
    nca_disposal_loss_indirect      NUMERIC(20,2),  -- 处置非流动资产的损失(ID=139)
    fixed_asset_scrap_loss          NUMERIC(20,2),  -- 固定资产报废损失(ID=140)
    fv_loss_indirect                NUMERIC(20,2),  -- 公允价值变动损失(ID=141)
    finance_expense_indirect        NUMERIC(20,2),  -- 财务费用(间接法)(ID=142)
    invest_loss_indirect            NUMERIC(20,2),  -- 投资损失(间接法)(ID=143)
    deferred_tax_asset_decrease     NUMERIC(20,2),  -- 递延所得税资产减少(ID=144)
    deferred_tax_liab_increase      NUMERIC(20,2),  -- 递延所得税负债增加(ID=145)
    inventory_decrease              NUMERIC(20,2),  -- 存货的减少(ID=146)
    op_receivable_decrease          NUMERIC(20,2),  -- 经营性应收减少(ID=147)
    op_payable_increase             NUMERIC(20,2),  -- 经营性应付增加(ID=148)
    other_indirect                  NUMERIC(20,2),  -- 其他(间接法)(ID=149)
    op_net_cash_flow_indirect       NUMERIC(20,2),  -- 经营净现金流2(ID=150)

    -- 【补充】
    debt_to_capital                 NUMERIC(20,2),  -- 债务转为资本(ID=151)
    convertible_bond_1y             NUMERIC(20,2),  -- 一年内可转债(ID=152)
    finance_lease_fixed_asset       NUMERIC(20,2),  -- 融资租入固定资产(ID=153)
    cash_end_balance_supplement     NUMERIC(20,2),  -- 现金期末余额(补充)(ID=154)
    cash_begin_balance_supplement   NUMERIC(20,2),  -- 现金期初余额(补充)(ID=155)
    cash_equiv_end_balance          NUMERIC(20,2),  -- 现金等价物期末余额(ID=156)
    cash_equiv_begin_balance        NUMERIC(20,2),  -- 现金等价物期初余额(ID=157)
    cash_net_increase_supplement    NUMERIC(20,2),  -- 现金净增加额(补充)(ID=158)

    -- 【近一年指标】
    ttm_op_cash_flow                NUMERIC(20,2),  -- 近一年经营现金流净额(ID=307)
    ttm_net_cash_flow               NUMERIC(20,2),  -- 近一年现金净流量(ID=310)
    ttm_inv_cash_flow               NUMERIC(20,2),  -- 近一年投资活动现金流净额(ID=316, 万元)

    -- 【新现金流量表 New CF (561-580)】
    other_cash_effect_end           NUMERIC(20,2),  -- 其他原因对现金影响2(ID=561, 万元)
    deposit_interbank_increase      NUMERIC(20,2),  -- 客户存款同业存放净增加(ID=562, 万元)
    central_bank_borrow_increase    NUMERIC(20,2),  -- 向央行借款净增加(ID=563, 万元)
    interbank_borrow_increase       NUMERIC(20,2),  -- 向其他金融机构拆入资金(ID=564, 万元)
    insurance_premium_receipt       NUMERIC(20,2),  -- 收到原保险合同保费(ID=565, 万元)
    reinsurance_net_receipt         NUMERIC(20,2),  -- 收到再保险业务现金(ID=566, 万元)
    deposit_invest_increase         NUMERIC(20,2),  -- 保户储金投资款净增加(ID=567, 万元)
    fv_fin_asset_disposal_incr      NUMERIC(20,2),  -- 处置以FV计量的金融资产(ID=568, 万元)
    interest_fee_cash_receipt       NUMERIC(20,2),  -- 收取利息手续费现金(ID=569, 万元)
    borrowing_increase              NUMERIC(20,2),  -- 拆入资金净增加(ID=570, 万元)
    repo_cash_increase              NUMERIC(20,2),  -- 回购业务资金净增加(ID=571, 万元)
    loan_advance_increase           NUMERIC(20,2),  -- 客户贷款垫款净增加(ID=572, 万元)
    central_bank_deposit_incr       NUMERIC(20,2),  -- 存放央行同业款项净增加(ID=573, 万元)
    insurance_claim_payment         NUMERIC(20,2),  -- 支付原保险合同赔付款(ID=574, 万元)
    interest_fee_payment            NUMERIC(20,2),  -- 支付利息手续费现金(ID=575, 万元)
    policy_dividend_payment         NUMERIC(20,2),  -- 支付保单红利现金(ID=576, 万元)
    subsidiary_minority_invest      NUMERIC(20,2),  -- 子公司吸收少数股东投资(ID=577, 万元)
    subsidiary_minority_dividend    NUMERIC(20,2),  -- 子公司支付少数股东股利(ID=578, 万元)
    invest_property_depreciation    NUMERIC(20,2),  -- 投资性房地产折旧摊销(ID=579, 万元)
    credit_impairment_cf            NUMERIC(20,2),  -- 信用减值损失(CF)(ID=580, 万元)

    source     TEXT NOT NULL DEFAULT 'mootdx',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, report_date)
);

CREATE TABLE IF NOT EXISTS financial_ratio (
    symbol      TEXT NOT NULL,
    report_date DATE NOT NULL,

    -- 【偿债能力 Solvency (159-171)】
    current_ratio                   NUMERIC(10,4),  -- 流动比率(ID=159)
    quick_ratio                     NUMERIC(10,4),  -- 速动比率(ID=160)
    cash_ratio                      NUMERIC(10,4),  -- 现金比率(ID=161, %)
    interest_coverage               NUMERIC(10,4),  -- 利息保障倍数(ID=162)
    non_current_liab_ratio          NUMERIC(10,4),  -- 非流动负债比率(ID=163, %)
    current_liab_ratio              NUMERIC(10,4),  -- 流动负债比率(ID=164, %)
    cash_maturity_debt_ratio        NUMERIC(10,4),  -- 现金到期债务比率(ID=165, %)
    tangible_asset_debt_ratio       NUMERIC(10,4),  -- 有形资产净值债务率(ID=166, %)
    equity_multiplier               NUMERIC(10,4),  -- 权益乘数(ID=167, %)
    equity_to_liab                  NUMERIC(10,4),  -- 股东权益/负债合计(ID=168, %)
    tangible_asset_to_liab          NUMERIC(10,4),  -- 有形资产/负债合计(ID=169, %)
    op_cf_to_liab                   NUMERIC(10,4),  -- 经营净现金流/负债合计(ID=170, %)
    ebitda_to_liab                  NUMERIC(10,4),  -- EBITDA/负债合计(ID=171, %)

    -- 【经营效率 Efficiency (172-182)】
    ar_turnover                     NUMERIC(10,4),  -- 应收账款周转率(ID=172)
    inventory_turnover              NUMERIC(10,4),  -- 存货周转率(ID=173)
    working_capital_turnover        NUMERIC(10,4),  -- 运营资金周转率(ID=174)
    asset_turnover                  NUMERIC(10,4),  -- 总资产周转率(ID=175)
    fixed_asset_turnover            NUMERIC(10,4),  -- 固定资产周转率(ID=176)
    ar_turnover_days                NUMERIC(10,4),  -- 应收账款周转天数(ID=177)
    inventory_turnover_days         NUMERIC(10,4),  -- 存货周转天数(ID=178)
    current_asset_turnover          NUMERIC(10,4),  -- 流动资产周转率(ID=179)
    current_asset_turnover_days     NUMERIC(10,4),  -- 流动资产周转天数(ID=180)
    asset_turnover_days             NUMERIC(10,4),  -- 总资产周转天数(ID=181)
    equity_turnover                 NUMERIC(10,4),  -- 股东权益周转率(ID=182)

    -- 【发展能力 Growth (183-192)】
    revenue_growth                  NUMERIC(10,4),  -- 营业收入增长率(ID=183, %)
    net_profit_growth               NUMERIC(10,4),  -- 净利润增长率(ID=184, %)
    net_asset_growth                NUMERIC(10,4),  -- 净资产增长率(ID=185, %)
    fixed_asset_growth              NUMERIC(10,4),  -- 固定资产增长率(ID=186, %)
    asset_growth                    NUMERIC(10,4),  -- 总资产增长率(ID=187, %)
    invest_income_growth            NUMERIC(10,4),  -- 投资收益增长率(ID=188, %)
    op_profit_growth                NUMERIC(10,4),  -- 营业利润增长率(ID=189, %)
    deduct_eps_growth               NUMERIC(10,4),  -- 扣非每股收益同比(ID=190, %)
    deduct_profit_growth            NUMERIC(10,4),  -- 扣非净利润同比(ID=191, %)

    -- 【获利能力 Profitability (193-209)】
    cost_profit_margin              NUMERIC(10,4),  -- 成本费用利润率(ID=193, %)
    op_profit_margin                NUMERIC(10,4),  -- 营业利润率(ID=194)
    biz_tax_rate                    NUMERIC(10,4),  -- 营业税金率(ID=195, %)
    cost_rate                       NUMERIC(10,4),  -- 营业成本率(ID=196, %)
    roe                             NUMERIC(10,4),  -- 净资产收益率(ID=197)
    roi                             NUMERIC(10,4),  -- 投资收益率(ID=198)
    net_profit_margin               NUMERIC(10,4),  -- 销售净利率(ID=199, %)
    roa                             NUMERIC(10,4),  -- 总资产报酬率(ID=200)
    profit_margin                   NUMERIC(10,4),  -- 净利润率(ID=201, %)
    gross_margin                    NUMERIC(10,4),  -- 销售毛利率(ID=202, %)
    three_fee_ratio                 NUMERIC(10,4),  -- 三费比重(ID=203, %)
    admin_expense_ratio             NUMERIC(10,4),  -- 管理费用率(ID=204, %)
    finance_expense_ratio           NUMERIC(10,4),  -- 财务费用率(ID=205, %)
    deduct_profit                   NUMERIC(20,2),  -- 扣非净利润(ID=206)
    ebit                            NUMERIC(20,2),  -- 息税前利润(ID=207)
    ebitda                          NUMERIC(20,2),  -- 息税折旧摊销前利润(ID=208)
    ebitda_margin                   NUMERIC(10,4),  -- EBITDA/营业总收入(ID=209, %)

    -- 【资本结构 Capital Structure (210-218)】
    debt_ratio                      NUMERIC(10,4),  -- 资产负债率(ID=210, %)
    current_asset_ratio             NUMERIC(10,4),  -- 流动资产比率(ID=211, %)
    cash_asset_ratio                NUMERIC(10,4),  -- 货币资金比率(ID=212, %)
    inventory_asset_ratio           NUMERIC(10,4),  -- 存货比率(ID=213, %)
    fixed_asset_ratio               NUMERIC(10,4),  -- 固定资产比率(ID=214)
    liab_structure_ratio            NUMERIC(10,4),  -- 负债结构比(ID=215, %)
    parent_equity_to_capital        NUMERIC(10,4),  -- 归母权益/全部投入资本(ID=216, %)
    equity_to_interest_debt         NUMERIC(10,4),  -- 股东权益/带息债务(ID=217, %)
    tangible_asset_to_net_debt      NUMERIC(10,4),  -- 有形资产/净债务(ID=218, %)

    -- 【现金流量分析 CF Analysis (219-229)】
    op_cf_per_share                 NUMERIC(10,4),  -- 每股经营现金流(ID=219, 元)
    revenue_cash_content            NUMERIC(10,4),  -- 营业收入现金含量(ID=220, %)
    op_cf_to_op_profit              NUMERIC(10,4),  -- 经营净现金流/经营净收益(ID=221, %)
    sale_receipt_to_revenue         NUMERIC(10,4),  -- 销售商品现金/营业收入(ID=222, %)
    op_cf_to_revenue                NUMERIC(10,4),  -- 经营净现金流/营业收入(ID=223)
    capex_to_depreciation           NUMERIC(10,4),  -- 资本支出/折旧摊销(ID=224)
    cf_per_share                    NUMERIC(10,4),  -- 每股现金流量净额(ID=225, 元)
    cash_short_term_debt_ratio      NUMERIC(10,4),  -- 经营净现金比率(短期)(ID=226, %)
    cash_total_debt_ratio           NUMERIC(10,4),  -- 经营净现金比率(全部)(ID=227, %)
    op_cf_to_net_profit             NUMERIC(10,4),  -- 经营净现金流/净利润(ID=228)
    all_asset_cash_recovery         NUMERIC(10,4),  -- 全部资产现金回收率(ID=229, %)

    -- 【近一年指标】
    ttm_net_profit                  NUMERIC(20,2),  -- 近一年净利润(ID=308, 万元)
    ttm_deduct_net_profit           NUMERIC(20,2),  -- 近一年扣非净利润(ID=309, 万元)

    source     TEXT NOT NULL DEFAULT 'mootdx',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, report_date)
);

CREATE TABLE IF NOT EXISTS financial_per_share (
    symbol      TEXT NOT NULL,
    report_date DATE NOT NULL,

    -- 【每股指标 Per Share (1-7)】
    eps                 NUMERIC(10,4),  -- 基本每股收益(ID=1)
    deduct_eps          NUMERIC(10,4),  -- 扣非每股收益(ID=2)
    retained_ps         NUMERIC(10,4),  -- 每股未分配利润(ID=3)
    bps                 NUMERIC(10,4),  -- 每股净资产(ID=4)
    capital_reserve_ps  NUMERIC(10,4),  -- 每股资本公积金(ID=5)
    roe_ps              NUMERIC(10,4),  -- 净资产收益率(ID=6)
    op_cf_ps            NUMERIC(10,4),  -- 每股经营现金流(ID=7)
    weighted_roe        NUMERIC(10,4),  -- 加权净资产收益率(ID=281)
    deduct_ps           NUMERIC(10,4),  -- 扣非每股收益(单季)(ID=282)

    -- 【单季度 Single Quarter (230-237)】
    sq_revenue            NUMERIC(20,2),  -- 单季营业收入(ID=230)
    sq_op_profit          NUMERIC(20,2),  -- 单季营业利润(ID=231)
    sq_parent_net_profit  NUMERIC(20,2),  -- 单季归母净利润(ID=232)
    sq_deduct_profit      NUMERIC(20,2),  -- 单季扣非净利润(ID=233)
    sq_op_cf              NUMERIC(20,2),  -- 单季经营现金流(ID=234)
    sq_inv_cf             NUMERIC(20,2),  -- 单季投资现金流(ID=235)
    sq_fin_cf             NUMERIC(20,2),  -- 单季筹资现金流(ID=236)
    sq_cash_change        NUMERIC(20,2),  -- 单季现金变动(ID=237)
    sq_eps                NUMERIC(10,4),  -- 单季基本每股收益(ID=311)
    sq_total_revenue      NUMERIC(20,2),  -- 单季营业总收入(ID=312, 万元)

    -- 【现金流 CF PS】
    cf_ps       NUMERIC(10,4),  -- 每股现金流量净额(ID=225, 元)
    ent_fcf_ps  NUMERIC(10,4),  -- 每股企业自由现金流(ID=321)
    eq_fcf_ps   NUMERIC(10,4),  -- 每股股东自由现金流(ID=322)

    source     TEXT NOT NULL DEFAULT 'mootdx',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, report_date)
);

CREATE TABLE IF NOT EXISTS financial_holdings (
    symbol      TEXT NOT NULL,
    report_date DATE NOT NULL,

    -- 【股本股东 Capital & Shareholders (238-245)】
    total_shares                    BIGINT,     -- 总股本(ID=238, 股)
    tradable_a_shares               BIGINT,     -- 已上市流通A股(ID=239, 股)
    tradable_b_shares               BIGINT,     -- 已上市流通B股(ID=240, 股)
    tradable_h_shares               BIGINT,     -- 已上市流通H股(ID=241, 股)
    shareholder_count               INTEGER,    -- 股东人数(ID=242, 户)
    top1_holder_shares              BIGINT,     -- 第一大股东持股(ID=243, 股)
    top10_tradable_holder_sum       BIGINT,     -- 十大流通股东持股合计(ID=244, 股)
    top10_holder_sum                BIGINT,     -- 十大股东持股合计(ID=245, 股)

    -- 【机构持股 Institutional Holdings (246-263)】
    inst_total_count                INTEGER,    -- 机构总数(ID=246, 家)
    inst_total_shares               BIGINT,     -- 机构持股总量(ID=247, 股)
    qfii_count                      INTEGER,    -- QFII机构数(ID=248)
    qfii_shares                     BIGINT,     -- QFII持股量(ID=249, 股)
    broker_count                    INTEGER,    -- 券商机构数(ID=250)
    broker_shares                   BIGINT,     -- 券商持股量(ID=251, 股)
    insurance_count                 INTEGER,    -- 保险机构数(ID=252)
    insurance_shares                BIGINT,     -- 保险持股量(ID=253, 股)
    fund_count                      INTEGER,    -- 基金机构数(ID=254)
    fund_shares                     BIGINT,     -- 基金持股量(ID=255, 股)
    social_security_count           INTEGER,    -- 社保机构数(ID=256)
    social_security_shares          BIGINT,     -- 社保持股量(ID=257, 股)
    private_equity_count            INTEGER,    -- 私募机构数(ID=258)
    private_equity_shares           BIGINT,     -- 私募持股量(ID=259, 股)
    finance_company_count           INTEGER,    -- 财务公司机构数(ID=260)
    finance_company_shares          BIGINT,     -- 财务公司持股量(ID=261, 股)
    pension_count                   INTEGER,    -- 年金机构数(ID=262)
    pension_shares                  BIGINT,     -- 年金持股量(ID=263, 股)

    -- 【机构持股补充 (272-280)】
    bank_count                      INTEGER,    -- 银行机构数(ID=272, 家)
    bank_shares                     BIGINT,     -- 银行持股量(ID=273, 股)
    general_legal_count             INTEGER,    -- 一般法人机构数(ID=274, 家)
    general_legal_shares            BIGINT,     -- 一般法人持股量(ID=275, 股)
    trust_count                     INTEGER,    -- 信托机构数(ID=277, 家)
    trust_shares                    BIGINT,     -- 信托持股量(ID=278, 股)
    special_legal_count             INTEGER,    -- 特殊法人机构数(ID=279, 家)
    special_legal_shares            BIGINT,     -- 特殊法人持股量(ID=280, 股)

    -- 【新增持股 (264-268)】
    top10_tradable_a_share_sum      BIGINT,         -- 十大流通股东A股合计(ID=264, 股)
    top1_tradable_holder_shares     BIGINT,         -- 第一大流通股东持股(ID=265, 股)
    free_float_shares               BIGINT,         -- 自由流通股(ID=266, 股)
    restricted_a_shares             BIGINT,         -- 受限流通A股(ID=267, 股)
    general_risk_reserve            NUMERIC(20,2),  -- 一般风险准备(ID=268)

    -- 【国家队 National Team (284)】
    national_team_shares            NUMERIC(20,2),  -- 国家队持股数量(ID=284, 万股)

    -- 【业绩预告/快报 Earnings Forecast (285-294, 313-315, 317-318)】
    forecast_net_profit_lower       NUMERIC(10,4),  -- 业绩预告净利润下限(ID=317, 万元)
    forecast_net_profit_upper       NUMERIC(10,4),  -- 业绩预告净利润上限(ID=318, 万元)
    forecast_profit_yoy_lower       NUMERIC(10,4),  -- 业绩预告净利润同比下限(ID=285, %)
    forecast_profit_yoy_upper       NUMERIC(10,4),  -- 业绩预告净利润同比上限(ID=286, %)
    fast_rep_parent_net_profit      NUMERIC(20,2),  -- 业绩快报归母净利润(ID=287)
    fast_rep_deduct_profit          NUMERIC(20,2),  -- 业绩快报扣非净利润(ID=288)
    fast_rep_total_asset            NUMERIC(20,2),  -- 业绩快报总资产(ID=289)
    fast_rep_net_asset              NUMERIC(20,2),  -- 业绩快报净资产(ID=290)
    fast_rep_eps                    NUMERIC(10,4),  -- 业绩快报每股收益(ID=291)
    fast_rep_diluted_roe            NUMERIC(10,4),  -- 业绩快报摊薄ROE(ID=292)
    fast_rep_weighted_roe           NUMERIC(10,4),  -- 业绩快报加权ROE(ID=293)
    fast_rep_bps                    NUMERIC(10,4),  -- 业绩快报每股净资产(ID=294)

    -- 【公告日期 Announcement Dates (313-315)】
    forecast_announce_date          TEXT,           -- 业绩预告公告日期(ID=313, YYMMDD)
    report_announce_date            TEXT,           -- 财报公告日期(ID=314, YYMMDD)
    fast_rep_announce_date          TEXT,           -- 业绩快报公告日期(ID=315, YYMMDD)

    -- 【员工 Employee (320)】
    employee_count                  INTEGER,        -- 员工总数(ID=320, 人)

    source     TEXT NOT NULL DEFAULT 'mootdx',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, report_date)
);

-- Indexes for cross-stock screening
CREATE INDEX IF NOT EXISTS idx_financial_ratio_roe             ON financial_ratio (roe);
CREATE INDEX IF NOT EXISTS idx_financial_ratio_debt_ratio      ON financial_ratio (debt_ratio);
CREATE INDEX IF NOT EXISTS idx_financial_ratio_net_profit_margin ON financial_ratio (net_profit_margin);
CREATE INDEX IF NOT EXISTS idx_financial_ratio_revenue_growth  ON financial_ratio (revenue_growth);
CREATE INDEX IF NOT EXISTS idx_financial_per_share_eps         ON financial_per_share (eps);
CREATE INDEX IF NOT EXISTS idx_financial_per_share_bps         ON financial_per_share (bps);
