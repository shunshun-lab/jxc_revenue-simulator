import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="JXC電子書籍収益シミュレーター", layout="centered")
st.title("📚 JXC：電子出版累計収益シミュレーター")

with st.sidebar:
    st.header("▶ 変数を入力")

    # 1️⃣ 売上・読了
    price = st.number_input(
        "販売価格 (¥)",
        50, 2000, 300, step=50,
        help="読者に表示される 1 冊あたりの税込販売価格"
    )
    initial_units = st.number_input(
        "初月の1冊あたり販売冊数",
        0, 10000, 50, step=10,
        help="発売初月に 1 冊あたり何冊売れるかの想定値"
    )
    sales_growth = st.slider(
        "月次販売成長率",
        0.0, 1.0, 0.1, step=0.05,
        help="販売冊数が毎月どれだけ伸びるか（10% = 0.10）"
    )

    initial_ku_pages = st.number_input(
        "初月KU読了ページ数/冊",
        0, 100000, 2000, step=500,
        help="Kindle Unlimited で 1 冊あたり読まれるページ数（初月）"
    )
    ku_growth = st.slider(
        "月次KU読了成長率",
        0.0, 1.0, 0.1, step=0.05,
        help="KU 読了ページ数の月次成長率（10% = 0.10）"
    )

    # 2️⃣ 書籍構成・刊行
    pages_per_book = st.number_input(
        "1冊あたりKENPページ数",
        10, 1000, 100, step=10,
        help="Kindle Edition Normalized Pages での本の長さ"
    )
    new_books_per_month = st.number_input(
        "毎月リリースする新刊数",
        0, 10, 1,
        help="毎月発行する新タイトル数"
    )
    months = st.number_input(
        "シミュレーション月数",
        1, 60, 24,
        help="収益を試算する期間（月）"
    )

    # 3️⃣ 配信・コスト
    royalty_rate = st.slider(
        "ロイヤリティ率",
        0.35, 0.7, 0.7, step=0.05,
        help="KDP の印税率（70% 帯は ¥250–¥1,250 に適用）"
    )
    kenp_rate = st.number_input(
        "KENP単価 (¥/p)",
        0.1, 2.0, 0.5, step=0.05,
        help="KU 読了 1 ページあたりの報酬（変動、通常 ¥0.45–0.55）"
    )
    file_size_mb = st.number_input(
        "ファイルサイズ (MB)",
        0.1, 10.0, 1.0, step=0.1,
        help="最終EPUBなどの容量。70%印税時は 1 MB ≈ ¥1 の配信コスト"
    )

    # 4️⃣ 分配方針
    st.markdown("---")
    revenue_share = st.slider(
        "関係者へ分配する還元率 %",
        0, 100, 70, step=5,
        help="総収益のうち、著者・編集者など関係者に配分する割合"
    )
    individual_share = st.slider(
        "↑のうち自分が受け取る割合 %",
        0, 100, 30, step=5,
        help="関係者還元分から自分個人が受け取るシェア"
    )

# ───────────────── 計算ロジック ───────────────── #
invest_rate = 100 - revenue_share
personal_rate = revenue_share / 100
individual_rate = individual_share / 100
royalty_per_sale = price * royalty_rate - file_size_mb

def monthly_vals(initial, growth, months):
    cur = initial
    for _ in range(months):
        yield cur
        cur *= (1 + growth)

sales_series = list(monthly_vals(initial_units, sales_growth, months))
ku_series = list(monthly_vals(initial_ku_pages, ku_growth, months))

records = []
total_books = 0
cum_total = cum_personal = cum_invest = cum_individual = 0

for m in range(months):
    total_books += new_books_per_month
    units_sold = sales_series[m] * total_books
    ku_pages = ku_series[m] * total_books
    rev_sales = units_sold * royalty_per_sale
    rev_ku = ku_pages * kenp_rate
    total_rev = rev_sales + rev_ku

    personal_rev = total_rev * personal_rate
    invest_rev = total_rev - personal_rev
    individual_rev = personal_rev * individual_rate

    cum_total += total_rev
    cum_personal += personal_rev
    cum_invest += invest_rev
    cum_individual += individual_rev

    records.append({
        "Month": m + 1,
        "Cumulative Total": cum_total,
        "Cumulative Personal": cum_personal,
        "Cumulative Investment": cum_invest,
        "Cumulative Individual": cum_individual
    })

df = pd.DataFrame(records)

# ───────────────── UI 出力 ───────────────── #
st.subheader("📊 収益按分の概要")
st.write(f"**関係者還元率:** {revenue_share}% | **投資率:** {invest_rate}% | **自分取り分:** {individual_share}%")
st.write(f"**最終累計額:** 総収益 ¥{cum_total:,.0f} / 還元 ¥{cum_personal:,.0f} / 投資 ¥{cum_invest:,.0f} / 自分 ¥{cum_individual:,.0f}")

# 折れ線用（投資線なし）
lines_df = df.melt(
    id_vars="Month",
    value_vars=["Cumulative Total", "Cumulative Personal", "Cumulative Individual"],
    var_name="Type", value_name="Value"
)

color_scale = alt.Scale(
    domain=["Cumulative Total", "Cumulative Personal", "Cumulative Individual"],
    range=["black", "#4f8cc9", "red"]
)

base = alt.Chart(df).encode(x=alt.X("Month:Q", axis=alt.Axis(title="Month")))
area_personal = base.mark_area(color="#b3d9ff", opacity=0.6).encode(
    y=alt.Y("Cumulative Personal:Q", axis=alt.Axis(title=""))
)
area_invest = base.mark_area(color="#c8e6c9", opacity=0.6).encode(
    y="Cumulative Total:Q", y2="Cumulative Personal:Q"
)

line_chart = alt.Chart(lines_df).mark_line(size=2).encode(
    x="Month:Q",
    y=alt.Y("Value:Q", axis=alt.Axis(title="")),
    color=alt.Color("Type:N", scale=color_scale, legend=alt.Legend(title="Legend")),
    strokeDash=alt.condition(
        alt.datum.Type == "Cumulative Individual",
        alt.value([4, 2]),
        alt.value([1, 0])
    )
)

chart = (area_personal + area_invest + line_chart).interactive()

st.subheader("📈 累計収益の推移")
st.altair_chart(chart, use_container_width=True)
st.markdown("🟩 緑の塗りつぶしは **投資積立**、水色は **関係者への還元** を示します。")

st.subheader("🔍 詳細テーブル")
st.dataframe(
    df.style.format({
        "Cumulative Total": "¥{:,.0f}",
        "Cumulative Personal": "¥{:,.0f}",
        "Cumulative Investment": "¥{:,.0f}",
        "Cumulative Individual": "¥{:,.0f}"
    })
)
