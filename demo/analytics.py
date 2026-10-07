import pandas as pd

from demo.pipeline import AS_OF


def filter_orders(orders, brands, suppliers, categories):
    return (
        orders.loc[
            orders["brand"].isin(brands)
            & orders["supplier"].isin(suppliers)
            & orders["category"].isin(categories)
        ].copy()
        if "supplier" in orders
        else orders.loc[
            orders["brand"].isin(brands)
            & orders["supplier_id"].isin(suppliers)
            & orders["category"].isin(categories)
        ].copy()
    )


def delivery(orders):
    result = orders.copy()
    complete = result["delivered_quantity"].ge(result["quantity"])
    received = result["delivered_date"].notna()
    result["status"] = "Upcoming"
    result.loc[result["due_date"].lt(AS_OF), "status"] = "Overdue"
    result.loc[complete & received, "status"] = "Late"
    result.loc[complete & received & result["delivered_date"].le(result["due_date"]), "status"] = (
        "On time"
    )
    result["month"] = result["due_date"].dt.strftime("%Y-%m")
    result["remaining_quantity"] = result["quantity"] - result["delivered_quantity"]
    return result


def summary(orders):
    quantity = orders["quantity"].sum()
    complete = orders["status"].isin(["On time", "Late"])
    return {
        "orders": len(orders),
        "quantity": int(quantity),
        "delivery_rate": float(orders["delivered_quantity"].sum() / quantity) if quantity else 0.0,
        "on_time_rate": float(orders.loc[complete, "status"].eq("On time").mean())
        if complete.any()
        else 0.0,
        "overdue_orders": int(orders["status"].eq("Overdue").sum()),
    }


def capacity(orders, suppliers):
    if not suppliers["monthly_capacity"].gt(0).all():
        raise ValueError("Monthly capacity must be positive")
    orders = orders.assign(month=orders["due_date"].dt.strftime("%Y-%m"))
    grouped = orders.groupby(["supplier_id", "month"], as_index=False)["quantity"].sum()
    result = grouped.merge(suppliers, on="supplier_id", validate="many_to_one")
    result["utilization"] = result["quantity"] / result["monthly_capacity"]
    result["available_quantity"] = result["monthly_capacity"] - result["quantity"]
    return result


def costing(orders, costs):
    result = orders.merge(costs, on="order_id", validate="one_to_one")
    result["unit_cost"] = result[["material", "labor", "overhead"]].sum(axis=1)
    result["variance"] = result["unit_cost"] / result["target"] - 1
    result["order_cost"] = result["quantity"] * result["unit_cost"]
    return result


def supplier_scorecard(orders):
    rows = []
    for supplier, group in orders.groupby("supplier"):
        metrics = summary(group)
        rows.append({"supplier": supplier, **metrics})
    return pd.DataFrame(rows)


def milestones(orders, stages):
    result = stages.merge(orders[["order_id", "brand", "supplier"]], on="order_id")
    result["status"] = "Upcoming"
    result.loc[result["planned_date"].lt(AS_OF), "status"] = "Overdue"
    done = result["completed_date"].notna()
    result.loc[done, "status"] = "Done late"
    result.loc[done & result["completed_date"].le(result["planned_date"]), "status"] = (
        "Done on time"
    )
    return result
