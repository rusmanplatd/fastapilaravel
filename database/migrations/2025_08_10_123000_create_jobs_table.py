from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from database.Schema.Migration import CreateTableMigration
from database.Schema.Blueprint import Blueprint
from app.Models.BaseModel import BaseModel


class CreateJobsTable(CreateTableMigration):
    """Create jobs table migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_jobs_table(table: Blueprint) -> None:
            table.id()
            table.string("queue").default("default").nullable(False).index()
            table.text("payload").nullable(False)
            table.integer("attempts").default(0).nullable(False)
            table.timestamp("reserved_at").nullable()
            table.timestamp("available_at").default_current_timestamp().nullable(False).index()
            table.boolean("is_reserved").default(False).nullable(False).index()
            table.string("worker_id").nullable()
            table.string("job_class").nullable(False)
            table.string("job_method").default("handle").nullable(False)
            table.integer("priority").default(0).nullable(False).index()
            table.integer("delay").default(0).nullable(False)
            table.string("connection").default("default").nullable(False)
            table.timestamps()
        
        self.create_table("jobs", create_jobs_table)


class Job(BaseModel):
    """Job model for queue system."""
    
    __tablename__ = "jobs"
    
    queue: Mapped[str] = mapped_column(String(255), nullable=False, default="default", index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    available_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.current_timestamp(), index=True)
    is_reserved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    worker_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    job_class: Mapped[str] = mapped_column(String(255), nullable=False)
    job_method: Mapped[str] = mapped_column(String(255), nullable=False, default="handle")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    delay: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    connection: Mapped[str] = mapped_column(String(255), nullable=False, default="default")
    
    def __str__(self) -> str:
        return f"Job(id={self.id}, queue={self.queue}, job_class={self.job_class})"
    
    def __repr__(self) -> str:
        return f"<Job(id={self.id}, queue='{self.queue}', job_class='{self.job_class}', attempts={self.attempts})>"