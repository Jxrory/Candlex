from mootdx.financial import financial

# 支持 .dat 和 .zip 两种格式，.zip 会自动解压找到 .dat 文件
df = financial.FinancialReader().to_data('./data/affair/gpcw20260331.zip')
print(df)
