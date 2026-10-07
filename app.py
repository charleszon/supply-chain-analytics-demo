import plotly.express as px
import streamlit as st

from demo import analytics, pipeline

st.set_page_config(page_title="Supply Chain Analytics Demo", layout="wide")
st.title("Supply Chain Analytics")
st.caption("Portfolio demonstration · entirely synthetic data · snapshot 15 July 2026")


def chart(figure):
    figure.update_layout(margin=dict(l=10, r=10, t=35, b=10), height=380)
    st.plotly_chart(figure, width="stretch")


def table(frame):
    st.dataframe(frame, width="stretch", hide_index=True)


def metrics(orders):
    values = analytics.summary(orders)
    cols = st.columns(4)
    cols[0].metric("Orders", f"{values['orders']:,}")
    cols[1].metric("Units received", f"{values['delivery_rate']:.1%}")
    cols[2].metric("On time · completed orders", f"{values['on_time_rate']:.1%}")
    cols[3].metric("Overdue orders", values["overdue_orders"])


def overview(orders, tables):
    metrics(orders)
    monthly = orders.groupby(["month", "status"], as_index=False)["quantity"].sum()
    chart(
        px.bar(
            monthly,
            x="month",
            y="quantity",
            color="status",
            title="Planned units by delivery status",
        )
    )
    st.subheader("Orders that need attention")
    overdue = orders.loc[orders["status"].eq("Overdue")].sort_values("due_date")
    if overdue.empty:
        st.info("No overdue orders in this selection.")
    else:
        table(overdue[["order_id", "supplier", "brand", "due_date", "remaining_quantity"]])
    st.caption("This demo illustrates operational questions; these are fictional outcomes.")


def deliveries(orders, tables):
    metrics(orders)
    status = orders.groupby("status", as_index=False).agg(
        orders=("order_id", "count"), units=("quantity", "sum")
    )
    chart(px.bar(status, x="status", y="orders", title="Order delivery status"))
    supplier = analytics.supplier_scorecard(orders)
    chart(
        px.bar(
            supplier, x="supplier", y="on_time_rate", title="On-time rate among completed orders"
        )
    )
    table(
        orders[
            [
                "order_id",
                "brand",
                "supplier",
                "quantity",
                "delivered_quantity",
                "due_date",
                "delivered_date",
                "status",
            ]
        ]
    )


def capacities(orders, tables):
    capacity = analytics.capacity(orders, tables["suppliers"])
    alerts = capacity.loc[capacity["utilization"].gt(1)]
    st.metric("Supplier-months above capacity", len(alerts))
    chart(
        px.bar(
            capacity,
            x="month",
            y="utilization",
            color="supplier",
            barmode="group",
            title="Monthly planned volume / capacity",
        )
    )
    st.caption("1.0 means 100% utilization. Monthly capacity is a fictional planning input.")
    table(
        capacity[
            [
                "supplier",
                "month",
                "quantity",
                "monthly_capacity",
                "utilization",
                "available_quantity",
            ]
        ]
    )


def costs(orders, tables):
    cost = analytics.costing(orders, tables["costs"])
    unit = cost["order_cost"].sum() / cost["quantity"].sum()
    cols = st.columns(3)
    cols[0].metric("Weighted unit cost", f"Rp {unit:,.0f}")
    cols[1].metric("Orders above target", int(cost["variance"].gt(0).sum()))
    cols[2].metric("Total planned cost", f"Rp {cost['order_cost'].sum():,.0f}")
    chart(
        px.box(
            cost,
            x="category",
            y="unit_cost",
            color="category",
            title="Synthetic unit cost distribution (IDR)",
        )
    )
    table(
        cost[
            [
                "order_id",
                "category",
                "supplier",
                "material",
                "labor",
                "overhead",
                "unit_cost",
                "target",
                "variance",
            ]
        ]
    )


def simulator(orders, tables):
    cost = analytics.costing(orders, tables["costs"])
    category = st.selectbox("Comparable product category", sorted(cost["category"].unique()))
    comparable = cost.loc[cost["category"].eq(category)]
    cols = st.columns(3)
    inputs = [
        cols[i].number_input(
            f"{component.title()} · IDR per unit",
            min_value=0,
            value=int(comparable[component].median()),
            step=1000,
        )
        for i, component in enumerate(["material", "labor", "overhead"])
    ]
    quote = sum(inputs)
    benchmark = comparable["unit_cost"].median()
    st.metric(
        "Proposed unit cost",
        f"Rp {quote:,.0f}",
        f"{quote / benchmark - 1:+.1%} vs synthetic category median",
        delta_color="inverse",
    )
    st.write(f"{len(comparable)} fictional comparable orders; median Rp {benchmark:,.0f}.")
    st.caption("Illustrative comparison only. It does not estimate a real market price.")
    table(comparable[["order_id", "supplier", "unit_cost", "target"]])


def schedule(orders, tables):
    schedule = tables["schedule"].merge(
        orders[["order_id", "supplier", "brand", "quantity"]], on="order_id"
    )
    supplier = st.selectbox("Schedule supplier", sorted(schedule["supplier"].unique()))
    schedule = schedule.loc[schedule["supplier"].eq(supplier)]
    chart(
        px.timeline(
            schedule,
            x_start="start_date",
            x_end="end_date",
            y="line",
            color="brand",
            hover_data=["order_id", "quantity"],
            title=f"{supplier} · planned production slots",
        )
    )
    st.caption("Slots are independently generated. Overlaps are visible for planning review.")
    table(schedule[["order_id", "line", "brand", "start_date", "end_date", "quantity"]])


def calendar(orders, tables):
    stages = analytics.milestones(orders, tables["milestones"])
    complete = stages["completed_date"].notna().mean()
    cols = st.columns(2)
    cols[0].metric("Milestones complete", f"{complete:.1%}")
    cols[1].metric("Overdue milestones", int(stages["status"].eq("Overdue").sum()))
    grouped = stages.groupby(["stage", "status"], as_index=False).size()
    chart(
        px.bar(
            grouped,
            x="stage",
            y="size",
            color="status",
            title="Development milestones by completion state",
        )
    )
    table(
        stages[
            ["order_id", "brand", "supplier", "stage", "planned_date", "completed_date", "status"]
        ].sort_values("planned_date")
    )


def suppliers(orders, tables):
    scorecard = analytics.supplier_scorecard(orders)
    chart(
        px.scatter(
            scorecard,
            x="delivery_rate",
            y="on_time_rate",
            size="quantity",
            color="supplier",
            hover_data=["orders", "overdue_orders"],
            title="Supplier completion and punctuality",
        )
    )
    table(scorecard)
    footprint = orders.groupby(["supplier", "category", "brand"], as_index=False)["quantity"].sum()
    chart(
        px.sunburst(
            footprint,
            path=["supplier", "category", "brand"],
            values="quantity",
            title="Historical allocation footprint · synthetic",
        )
    )


VIEWS = {
    "Overview": overview,
    "Delivery": deliveries,
    "Capacity": capacities,
    "Costing": costs,
    "Cost simulator": simulator,
    "Production schedule": schedule,
    "Milestones": calendar,
    "Supplier intelligence": suppliers,
}

try:
    tables = pipeline.load()
except (OSError, ValueError):
    st.error("The demo warehouse could not be loaded. Rebuild it with the documented command.")
    st.stop()

orders = analytics.delivery(
    tables["orders"].merge(
        tables["suppliers"][["supplier_id", "supplier"]], on="supplier_id", validate="many_to_one"
    )
)
with st.sidebar:
    st.header("Explore the demo")
    page = st.radio("View", list(VIEWS))
    brands = st.multiselect(
        "Brands", sorted(orders["brand"].unique()), default=sorted(orders["brand"].unique())
    )
    suppliers_selected = st.multiselect(
        "Suppliers",
        sorted(orders["supplier"].unique()),
        default=sorted(orders["supplier"].unique()),
    )
    categories = st.multiselect(
        "Categories",
        sorted(orders["category"].unique()),
        default=sorted(orders["category"].unique()),
    )
    months = st.multiselect(
        "Due months", sorted(orders["month"].unique()), default=sorted(orders["month"].unique())
    )
    st.caption("All names, prices, capacities, dates, and records are invented.")

filtered = analytics.filter_orders(orders, brands, suppliers_selected, categories)
filtered = filtered.loc[filtered["month"].isin(months)]
st.header(page)
if filtered.empty:
    st.info("No orders match the selected filters. Select at least one value in each filter.")
else:
    VIEWS[page](filtered, tables)
    st.download_button(
        "Download filtered orders · CSV",
        filtered.to_csv(index=False).encode("utf-8"),
        file_name="synthetic_orders.csv",
        mime="text/csv",
    )
