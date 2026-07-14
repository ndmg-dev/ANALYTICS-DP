import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import EmployeeRecord, MetricResult, Snapshot
from datetime import datetime

class MetricsEngine:
    def __init__(self, db: Session):
        self.db = db

    def compute_and_save_metrics(self, snapshot_id: int):
        snapshot = self.db.get(Snapshot, snapshot_id)
        if not snapshot:
            raise ValueError(f"Snapshot {snapshot_id} not found")

        stmt = select(EmployeeRecord).where(EmployeeRecord.snapshot_id == snapshot_id)
        records = self.db.scalars(stmt).all()
        
        if not records:
            return

        # Convert to DataFrame for analytical processing
        data = [
            {
                "code": r.code,
                "job_title": r.job_title,
                "category": r.category,
                "monthly_hours": r.monthly_hours,
                "children_count": r.children_count,
                "dependents_count": r.dependents_count,
                "admission_date": r.admission_date,
                "fgts_option": r.fgts_option,
                "union_contribution": r.union_contribution,
                "salary": r.salary
            }
            for r in records
        ]
        df = pd.DataFrame(data)

        metrics_to_save = []

        # 1. Active Headcount
        active_headcount = df["code"].nunique()
        metrics_to_save.append(("active_headcount", float(active_headcount)))

        # 2. Average/Median Monthly Hours
        if not df["monthly_hours"].isnull().all():
            metrics_to_save.append(("avg_monthly_hours", float(df["monthly_hours"].mean())))
            metrics_to_save.append(("median_monthly_hours", float(df["monthly_hours"].median())))

        # 3. Children and Dependents
        if not df["children_count"].isnull().all():
            metrics_to_save.append(("total_children", float(df["children_count"].sum())))
            metrics_to_save.append(("avg_children", float(df["children_count"].mean())))

        if not df["dependents_count"].isnull().all():
            metrics_to_save.append(("total_dependents", float(df["dependents_count"].sum())))
            metrics_to_save.append(("avg_dependents", float(df["dependents_count"].mean())))

        # 4. FGTS and Union Rates
        if not df["fgts_option"].isnull().all():
            fgts_rate = df["fgts_option"].sum() / df["fgts_option"].count()
            metrics_to_save.append(("fgts_option_rate", float(fgts_rate)))

        if not df["union_contribution"].isnull().all():
            union_rate = df["union_contribution"].sum() / df["union_contribution"].count()
            metrics_to_save.append(("union_contribution_rate", float(union_rate)))

        # 5. Tenure (in days)
        valid_dates = df.dropna(subset=["admission_date"])
        if not valid_dates.empty:
            ref_date = pd.to_datetime(snapshot.reference_date)
            # Ensure admission_date is datetime
            df["admission_date"] = pd.to_datetime(df["admission_date"])
            tenure_days = (ref_date - df["admission_date"]).dt.days
            
            metrics_to_save.append(("avg_tenure_days", float(tenure_days.mean())))
            metrics_to_save.append(("median_tenure_days", float(tenure_days.median())))

        # 6. Salary (Only if authorized and supported, will just compute raw if present)
        if not df["salary"].isnull().all():
            metrics_to_save.append(("total_payroll", float(df["salary"].sum())))
            metrics_to_save.append(("avg_salary", float(df["salary"].mean())))

        # Clear old metrics and save new ones
        self.db.query(MetricResult).filter(MetricResult.snapshot_id == snapshot_id).delete()

        for metric_id, val in metrics_to_save:
            mr = MetricResult(
                snapshot_id=snapshot_id,
                metric_id=metric_id,
                metric_value=val,
                calculated_at=datetime.utcnow()
            )
            self.db.add(mr)
        
        self.db.commit()

    def get_distributions(self, snapshot_id: int):
        stmt = select(EmployeeRecord).where(EmployeeRecord.snapshot_id == snapshot_id)
        records = self.db.scalars(stmt).all()
        
        if not records:
            return {}

        snapshot = self.db.get(Snapshot, snapshot_id)
        ref_date = pd.to_datetime(snapshot.reference_date)

        data = []
        for r in records:
            data.append({
                "name": r.name,
                "job_title": r.job_title,
                "category": r.category,
                "monthly_hours": r.monthly_hours,
                "admission_date": r.admission_date,
                "salary": r.salary,
                "company": (r.raw_data or {}).get("company", "Mendonça Galvão Contadores Associados")
            })
        df = pd.DataFrame(data)
        
        def get_rich_dist(col_name):
            if col_name not in df.columns or df[col_name].isnull().all():
                return {}
            dist = {}
            # Sort by count descending
            counts = df[col_name].value_counts()
            for val in counts.index:
                group = df[df[col_name] == val]
                str_val = str(val) if not pd.isna(val) else "N/D"
                dist[str_val] = {
                    "count": len(group),
                    "employees": group["name"].tolist()
                }
            return dist

        job_titles_dist = get_rich_dist("job_title")
        company_dist = get_rich_dist("company")

        # Tenure Distribution
        tenure_dist = {
            "< 1 ano": {"count": 0, "employees": []},
            "1-3 anos": {"count": 0, "employees": []},
            "3-5 anos": {"count": 0, "employees": []},
            "> 5 anos": {"count": 0, "employees": []}
        }
        if not df["admission_date"].isnull().all():
            df["admission_date"] = pd.to_datetime(df["admission_date"])
            years = (ref_date - df["admission_date"]).dt.days / 365.25
            for idx, y in years.dropna().items():
                emp_name = df.loc[idx, "name"]
                if y < 1: 
                    tenure_dist["< 1 ano"]["count"] += 1
                    tenure_dist["< 1 ano"]["employees"].append(emp_name)
                elif y <= 3: 
                    tenure_dist["1-3 anos"]["count"] += 1
                    tenure_dist["1-3 anos"]["employees"].append(emp_name)
                elif y <= 5: 
                    tenure_dist["3-5 anos"]["count"] += 1
                    tenure_dist["3-5 anos"]["employees"].append(emp_name)
                else: 
                    tenure_dist["> 5 anos"]["count"] += 1
                    tenure_dist["> 5 anos"]["employees"].append(emp_name)

        # Remove empty buckets for cleaner UI
        tenure_dist = {k: v for k, v in tenure_dist.items() if v["count"] > 0}

        return {
            "job_title": job_titles_dist,
            "company": company_dist,
            "tenure": tenure_dist
        }
