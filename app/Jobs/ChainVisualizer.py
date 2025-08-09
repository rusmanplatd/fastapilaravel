"""
Advanced Job Chain Visualization and Debugging System
"""
from __future__ import annotations

import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict
import io
import base64

from app.Jobs.Chain import JobChain, ChainStatus, ChainStep
from app.Jobs.ChainRegistry import ChainRegistry
from app.Jobs.MetricsCollector import get_metrics_collector, JobPhase
from app.Jobs.RetryManager import get_retry_manager
from app.Jobs.ChainMonitor import get_chain_monitor


class VisualizationType(Enum):
    """Types of visualizations available."""
    FLOW_DIAGRAM = "flow_diagram"
    TIMELINE = "timeline"
    DEPENDENCY_GRAPH = "dependency_graph"
    EXECUTION_TRACE = "execution_trace"
    PERFORMANCE_HEATMAP = "performance_heatmap"


class NodeType(Enum):
    """Types of nodes in visualization."""
    JOB = "job"
    CHAIN = "chain"
    DECISION = "decision"
    PARALLEL = "parallel"
    ERROR = "error"
    RETRY = "retry"


@dataclass
class VisualizationNode:
    """A node in the visualization graph."""
    id: str
    type: NodeType
    label: str
    status: str
    properties: Dict[str, Any]
    position: Optional[Tuple[int, int]] = None
    style: Dict[str, str] = None
    
    def __post_init__(self):
        if self.style is None:
            self.style = self._default_style()
    
    def _default_style(self) -> Dict[str, str]:
        """Get default styling based on node type and status."""
        base_style = {
            "border-radius": "5px",
            "padding": "10px",
            "text-align": "center",
            "font-family": "Arial, sans-serif",
            "font-size": "12px"
        }
        
        # Status-based coloring
        if self.status == "completed":
            base_style["background-color"] = "#28a745"
            base_style["color"] = "white"
        elif self.status == "running":
            base_style["background-color"] = "#007bff"
            base_style["color"] = "white"
        elif self.status == "failed":
            base_style["background-color"] = "#dc3545"
            base_style["color"] = "white"
        elif self.status == "pending":
            base_style["background-color"] = "#ffc107"
            base_style["color"] = "black"
        else:
            base_style["background-color"] = "#6c757d"
            base_style["color"] = "white"
        
        # Type-specific styling
        if self.type == NodeType.DECISION:
            base_style["border-radius"] = "50%"
        elif self.type == NodeType.ERROR:
            base_style["border"] = "3px solid #dc3545"
        elif self.type == NodeType.RETRY:
            base_style["border"] = "2px dashed #ffc107"
        
        return base_style


@dataclass
class VisualizationEdge:
    """An edge connecting nodes in the visualization."""
    id: str
    source: str
    target: str
    label: Optional[str] = None
    style: Dict[str, str] = None
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.style is None:
            self.style = {
                "stroke": "#666",
                "stroke-width": "2px",
                "fill": "none"
            }
        if self.properties is None:
            self.properties = {}


@dataclass
class VisualizationLayout:
    """Layout information for the visualization."""
    type: str  # hierarchical, circular, force-directed, etc.
    direction: str = "top-to-bottom"  # left-to-right, top-to-bottom, etc.
    spacing: Dict[str, int] = None
    
    def __post_init__(self):
        if self.spacing is None:
            self.spacing = {
                "node": 150,
                "rank": 100,
                "edge": 10
            }


@dataclass
class VisualizationData:
    """Complete visualization data structure."""
    id: str
    title: str
    type: VisualizationType
    nodes: List[VisualizationNode]
    edges: List[VisualizationEdge]
    layout: VisualizationLayout
    metadata: Dict[str, Any]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type.value,
            "nodes": [asdict(node) for node in self.nodes],
            "edges": [asdict(edge) for edge in self.edges],
            "layout": asdict(self.layout),
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }
    
    def to_mermaid(self) -> str:
        """Generate Mermaid diagram syntax."""
        lines = ["graph TD"]
        
        # Add nodes
        for node in self.nodes:
            shape_start, shape_end = self._mermaid_node_shape(node.type)
            lines.append(f"    {node.id}{shape_start}{node.label}{shape_end}")
        
        # Add edges
        for edge in self.edges:
            if edge.label:
                lines.append(f"    {edge.source} -->|{edge.label}| {edge.target}")
            else:
                lines.append(f"    {edge.source} --> {edge.target}")
        
        # Add styling
        for node in self.nodes:
            if node.status == "completed":
                lines.append(f"    classDef completed fill:#28a745,stroke:#1e7e34,color:#fff")
                lines.append(f"    class {node.id} completed")
            elif node.status == "running":
                lines.append(f"    classDef running fill:#007bff,stroke:#0056b3,color:#fff")
                lines.append(f"    class {node.id} running")
            elif node.status == "failed":
                lines.append(f"    classDef failed fill:#dc3545,stroke:#c82333,color:#fff")
                lines.append(f"    class {node.id} failed")
        
        return "\n".join(lines)
    
    def _mermaid_node_shape(self, node_type: NodeType) -> Tuple[str, str]:
        """Get Mermaid node shape syntax."""
        shapes = {
            NodeType.JOB: ("[", "]"),
            NodeType.CHAIN: ("((", "))"),
            NodeType.DECISION: ("{", "}"),
            NodeType.PARALLEL: ("[", "]"),
            NodeType.ERROR: ("([", "])"),
            NodeType.RETRY: ("[[", "]]")
        }
        return shapes.get(node_type, ("[", "]"))


class ChainVisualizer:
    """Advanced job chain visualization and debugging system."""
    
    def __init__(self) -> None:
        self.registry = ChainRegistry.get_instance()
        self.metrics_collector = get_metrics_collector()
        self.retry_manager = get_retry_manager()
        self.monitor = get_chain_monitor()
        self._visualization_cache: Dict[str, VisualizationData] = {}
        self._lock = threading.RLock()
    
    def visualize_chain(
        self,
        chain_id: str,
        visualization_type: VisualizationType = VisualizationType.FLOW_DIAGRAM
    ) -> Optional[VisualizationData]:
        """Create a visualization for a specific job chain."""
        chain = self.registry.get_chain(chain_id)
        if not chain:
            return None
        
        with self._lock:
            viz_id = f"{chain_id}_{visualization_type.value}_{int(time.time())}"
            
            if visualization_type == VisualizationType.FLOW_DIAGRAM:
                viz_data = self._create_flow_diagram(viz_id, chain)
            elif visualization_type == VisualizationType.TIMELINE:
                viz_data = self._create_timeline(viz_id, chain)
            elif visualization_type == VisualizationType.EXECUTION_TRACE:
                viz_data = self._create_execution_trace(viz_id, chain)
            elif visualization_type == VisualizationType.PERFORMANCE_HEATMAP:
                viz_data = self._create_performance_heatmap(viz_id, chain)
            else:
                viz_data = self._create_flow_diagram(viz_id, chain)
            
            self._visualization_cache[viz_id] = viz_data
            return viz_data
    
    def _create_flow_diagram(self, viz_id: str, chain: JobChain) -> VisualizationData:
        """Create a flow diagram visualization."""
        nodes = []
        edges = []
        
        # Add chain start node
        start_node = VisualizationNode(
            id="start",
            type=NodeType.CHAIN,
            label=f"Start: {chain.name}",
            status="completed" if chain.current_step > 0 else "pending",
            properties={"chain_id": chain.chain_id, "step_index": -1}
        )
        nodes.append(start_node)
        
        # Add step nodes
        for i, step in enumerate(chain.steps):
            status = self._get_step_status(chain, i)
            
            node = VisualizationNode(
                id=f"step_{i}",
                type=NodeType.JOB,
                label=f"{step.name or f'Step {i+1}'}\n({type(step.job).__name__})",
                status=status,
                properties={
                    "step_index": i,
                    "job_type": type(step.job).__name__,
                    "delay": step.delay,
                    "retry_on_failure": step.retry_on_failure,
                    "continue_on_failure": step.continue_on_failure
                }
            )
            nodes.append(node)
            
            # Add retry nodes if applicable
            retry_info = self.retry_manager.get_retry_info(f"{chain.chain_id}_step_{i}")
            if retry_info and retry_info.attempts:
                retry_node = VisualizationNode(
                    id=f"retry_{i}",
                    type=NodeType.RETRY,
                    label=f"Retries: {len(retry_info.attempts)}",
                    status="failed" if retry_info.is_exhausted else "running",
                    properties={
                        "retry_count": len(retry_info.attempts),
                        "max_retries": retry_info.max_retries,
                        "is_exhausted": retry_info.is_exhausted
                    }
                )
                nodes.append(retry_node)
                
                # Edge from step to retry
                retry_edge = VisualizationEdge(
                    id=f"edge_step_{i}_retry",
                    source=f"step_{i}",
                    target=f"retry_{i}",
                    label="retry",
                    style={"stroke": "#ffc107", "stroke-dasharray": "5,5"}
                )
                edges.append(retry_edge)
        
        # Add edges between sequential steps
        prev_node = "start"
        for i, step in enumerate(chain.steps):
            edge = VisualizationEdge(
                id=f"edge_{prev_node}_step_{i}",
                source=prev_node,
                target=f"step_{i}",
                properties={"delay": step.delay}
            )
            
            if step.delay > 0:
                edge.label = f"delay: {step.delay}s"
                edge.style = {"stroke": "#ffc107", "stroke-width": "2px"}
            
            edges.append(edge)
            prev_node = f"step_{i}"
        
        # Add end node
        end_node = VisualizationNode(
            id="end",
            type=NodeType.CHAIN,
            label=f"End: {chain.status.value}",
            status="completed" if chain.status == ChainStatus.COMPLETED else chain.status.value,
            properties={"chain_status": chain.status.value}
        )
        nodes.append(end_node)
        
        if chain.steps:
            final_edge = VisualizationEdge(
                id=f"edge_final",
                source=f"step_{len(chain.steps)-1}",
                target="end"
            )
            edges.append(final_edge)
        
        layout = VisualizationLayout(type="hierarchical", direction="top-to-bottom")
        
        return VisualizationData(
            id=viz_id,
            title=f"Flow Diagram: {chain.name}",
            type=VisualizationType.FLOW_DIAGRAM,
            nodes=nodes,
            edges=edges,
            layout=layout,
            metadata={
                "chain_id": chain.chain_id,
                "total_steps": len(chain.steps),
                "current_step": chain.current_step,
                "status": chain.status.value
            },
            timestamp=datetime.now()
        )
    
    def _create_timeline(self, viz_id: str, chain: JobChain) -> VisualizationData:
        """Create a timeline visualization."""
        nodes = []
        edges = []
        
        # Get metrics for each step
        for i, step in enumerate(chain.steps):
            step_job_id = f"{chain.chain_id}_step_{i}"
            job_metrics = self.metrics_collector.get_job_metrics(step_job_id)
            
            status = self._get_step_status(chain, i)
            
            # Calculate timeline position
            if job_metrics:
                start_time = job_metrics.queued_at
                duration = job_metrics.processing_duration or 0
            else:
                start_time = datetime.now()
                duration = 0
            
            node = VisualizationNode(
                id=f"timeline_step_{i}",
                type=NodeType.JOB,
                label=f"{step.name or f'Step {i+1}'}\n{duration:.2f}s",
                status=status,
                properties={
                    "start_time": start_time.isoformat(),
                    "duration": duration,
                    "queued_at": job_metrics.queued_at.isoformat() if job_metrics else None,
                    "started_at": job_metrics.started_at.isoformat() if job_metrics and job_metrics.started_at else None,
                    "completed_at": job_metrics.completed_at.isoformat() if job_metrics and job_metrics.completed_at else None
                },
                position=(i * 200, 0)  # Horizontal timeline
            )
            nodes.append(node)
            
            # Add dependency edge
            if i > 0:
                edge = VisualizationEdge(
                    id=f"timeline_edge_{i-1}_{i}",
                    source=f"timeline_step_{i-1}",
                    target=f"timeline_step_{i}",
                    label="then"
                )
                edges.append(edge)
        
        layout = VisualizationLayout(type="timeline", direction="left-to-right")
        
        return VisualizationData(
            id=viz_id,
            title=f"Timeline: {chain.name}",
            type=VisualizationType.TIMELINE,
            nodes=nodes,
            edges=edges,
            layout=layout,
            metadata={
                "chain_id": chain.chain_id,
                "timeline_span": "calculated",
                "total_duration": "calculated"
            },
            timestamp=datetime.now()
        )
    
    def _create_execution_trace(self, viz_id: str, chain: JobChain) -> VisualizationData:
        """Create an execution trace with detailed logging."""
        nodes = []
        edges = []
        
        trace_events = self._collect_execution_trace(chain)
        
        for i, event in enumerate(trace_events):
            node = VisualizationNode(
                id=f"trace_{i}",
                type=NodeType.JOB,
                label=f"{event['timestamp'].strftime('%H:%M:%S')}\n{event['event']}\n{event['details']}",
                status=event['status'],
                properties=event
            )
            nodes.append(node)
            
            # Connect sequential events
            if i > 0:
                edge = VisualizationEdge(
                    id=f"trace_edge_{i-1}_{i}",
                    source=f"trace_{i-1}",
                    target=f"trace_{i}",
                    label=f"+{(event['timestamp'] - trace_events[i-1]['timestamp']).total_seconds():.2f}s"
                )
                edges.append(edge)
        
        layout = VisualizationLayout(type="hierarchical", direction="top-to-bottom")
        
        return VisualizationData(
            id=viz_id,
            title=f"Execution Trace: {chain.name}",
            type=VisualizationType.EXECUTION_TRACE,
            nodes=nodes,
            edges=edges,
            layout=layout,
            metadata={
                "chain_id": chain.chain_id,
                "trace_events": len(trace_events)
            },
            timestamp=datetime.now()
        )
    
    def _create_performance_heatmap(self, viz_id: str, chain: JobChain) -> VisualizationData:
        """Create a performance heatmap visualization."""
        nodes = []
        edges = []
        
        # Collect performance data for each step
        performance_data = []
        for i, step in enumerate(chain.steps):
            step_job_id = f"{chain.chain_id}_step_{i}"
            job_metrics = self.metrics_collector.get_job_metrics(step_job_id)
            
            if job_metrics:
                performance_data.append({
                    "step": i,
                    "duration": job_metrics.processing_duration or 0,
                    "memory": job_metrics.peak_memory_mb,
                    "cpu": job_metrics.cpu_usage_percent,
                    "success": job_metrics.success
                })
        
        # Create heatmap nodes based on performance intensity
        max_duration = max(p["duration"] for p in performance_data) if performance_data else 1
        
        for i, perf in enumerate(performance_data):
            intensity = perf["duration"] / max_duration
            
            # Color based on performance (red = slow, green = fast)
            if intensity > 0.8:
                color = "#dc3545"  # Red for slow
            elif intensity > 0.5:
                color = "#ffc107"  # Yellow for medium
            else:
                color = "#28a745"  # Green for fast
            
            node = VisualizationNode(
                id=f"heatmap_step_{i}",
                type=NodeType.JOB,
                label=f"Step {i+1}\n{perf['duration']:.2f}s\n{perf['memory']:.1f}MB",
                status="completed" if perf["success"] else "failed",
                properties=perf,
                style={
                    "background-color": color,
                    "color": "white",
                    "font-weight": "bold",
                    "border-radius": "10px",
                    "padding": "15px"
                }
            )
            nodes.append(node)
        
        layout = VisualizationLayout(type="grid", direction="left-to-right")
        
        return VisualizationData(
            id=viz_id,
            title=f"Performance Heatmap: {chain.name}",
            type=VisualizationType.PERFORMANCE_HEATMAP,
            nodes=nodes,
            edges=edges,
            layout=layout,
            metadata={
                "chain_id": chain.chain_id,
                "performance_summary": {
                    "total_duration": sum(p["duration"] for p in performance_data),
                    "avg_duration": sum(p["duration"] for p in performance_data) / len(performance_data) if performance_data else 0,
                    "max_memory": max(p["memory"] for p in performance_data) if performance_data else 0,
                    "success_rate": sum(1 for p in performance_data if p["success"]) / len(performance_data) if performance_data else 0
                }
            },
            timestamp=datetime.now()
        )
    
    def _get_step_status(self, chain: JobChain, step_index: int) -> str:
        """Get the current status of a chain step."""
        if step_index < chain.current_step:
            return "completed"
        elif step_index == chain.current_step and chain.status == ChainStatus.RUNNING:
            return "running"
        elif step_index == chain.current_step and chain.status == ChainStatus.FAILED:
            return "failed"
        else:
            return "pending"
    
    def _collect_execution_trace(self, chain: JobChain) -> List[Dict[str, Any]]:
        """Collect detailed execution trace for a chain."""
        trace_events = []
        
        # Chain start event
        trace_events.append({
            "timestamp": datetime.now() - timedelta(minutes=len(chain.steps) * 2),  # Estimate
            "event": "CHAIN_START",
            "details": f"Chain '{chain.name}' started",
            "status": "running",
            "step_index": -1
        })
        
        # Step events
        for i, step in enumerate(chain.steps):
            step_job_id = f"{chain.chain_id}_step_{i}"
            job_metrics = self.metrics_collector.get_job_metrics(step_job_id)
            retry_info = self.retry_manager.get_retry_info(step_job_id)
            
            # Step queued
            if job_metrics:
                trace_events.append({
                    "timestamp": job_metrics.queued_at,
                    "event": "STEP_QUEUED",
                    "details": f"Step {i+1} queued",
                    "status": "pending",
                    "step_index": i
                })
                
                # Step started
                if job_metrics.started_at:
                    trace_events.append({
                        "timestamp": job_metrics.started_at,
                        "event": "STEP_STARTED",
                        "details": f"Step {i+1} started processing",
                        "status": "running",
                        "step_index": i
                    })
                
                # Step completed/failed
                if job_metrics.completed_at:
                    trace_events.append({
                        "timestamp": job_metrics.completed_at,
                        "event": "STEP_COMPLETED" if job_metrics.success else "STEP_FAILED",
                        "details": f"Step {i+1} {'completed' if job_metrics.success else 'failed'}",
                        "status": "completed" if job_metrics.success else "failed",
                        "step_index": i
                    })
            
            # Retry events
            if retry_info:
                for attempt in retry_info.attempts:
                    trace_events.append({
                        "timestamp": attempt.timestamp,
                        "event": "STEP_RETRY",
                        "details": f"Step {i+1} retry attempt {attempt.attempt_number}",
                        "status": "running",
                        "step_index": i,
                        "retry_attempt": attempt.attempt_number
                    })
        
        # Chain completion
        trace_events.append({
            "timestamp": datetime.now(),
            "event": "CHAIN_COMPLETED" if chain.status == ChainStatus.COMPLETED else "CHAIN_FAILED",
            "details": f"Chain '{chain.name}' {chain.status.value}",
            "status": chain.status.value,
            "step_index": -1
        })
        
        return sorted(trace_events, key=lambda x: x["timestamp"])
    
    def get_chain_debug_info(self, chain_id: str) -> Dict[str, Any]:
        """Get comprehensive debugging information for a chain."""
        chain = self.registry.get_chain(chain_id)
        if not chain:
            return {"error": "Chain not found"}
        
        debug_info = {
            "chain_info": {
                "id": chain_id,
                "name": chain.name,
                "status": chain.status.value,
                "current_step": chain.current_step,
                "total_steps": len(chain.steps),
                "created_at": "N/A"  # Would need to track creation time
            },
            "steps": [],
            "metrics": {},
            "retry_info": {},
            "health_checks": [],
            "performance": {},
            "errors": []
        }
        
        # Step information
        for i, step in enumerate(chain.steps):
            step_job_id = f"{chain_id}_step_{i}"
            job_metrics = self.metrics_collector.get_job_metrics(step_job_id)
            retry_info = self.retry_manager.get_retry_info(step_job_id)
            
            step_info = {
                "index": i,
                "name": step.name or f"Step {i+1}",
                "job_type": type(step.job).__name__,
                "status": self._get_step_status(chain, i),
                "delay": step.delay,
                "retry_on_failure": step.retry_on_failure,
                "continue_on_failure": step.continue_on_failure,
                "metrics": asdict(job_metrics) if job_metrics else None,
                "retry_attempts": len(retry_info.attempts) if retry_info else 0,
                "is_retrying": retry_info and not retry_info.is_exhausted if retry_info else False
            }
            debug_info["steps"].append(step_info)
        
        # Overall metrics
        overall_metrics = self.metrics_collector.get_overall_metrics(hours=1)
        debug_info["metrics"] = overall_metrics
        
        # Health checks
        health_info = self.monitor.get_current_health()
        debug_info["health_checks"] = health_info
        
        # Performance analysis
        debug_info["performance"] = self._analyze_chain_performance(chain)
        
        return debug_info
    
    def _analyze_chain_performance(self, chain: JobChain) -> Dict[str, Any]:
        """Analyze performance characteristics of a chain."""
        analysis = {
            "bottlenecks": [],
            "recommendations": [],
            "efficiency_score": 0.0,
            "resource_usage": {
                "peak_memory": 0.0,
                "avg_cpu": 0.0,
                "total_duration": 0.0
            }
        }
        
        step_durations = []
        step_memory = []
        
        for i, step in enumerate(chain.steps):
            step_job_id = f"{chain.chain_id}_step_{i}"
            job_metrics = self.metrics_collector.get_job_metrics(step_job_id)
            
            if job_metrics:
                if job_metrics.processing_duration:
                    step_durations.append(job_metrics.processing_duration)
                step_memory.append(job_metrics.peak_memory_mb)
                
                # Identify bottlenecks (steps taking >2x average time)
                if step_durations:
                    avg_duration = sum(step_durations) / len(step_durations)
                    if job_metrics.processing_duration > avg_duration * 2:
                        analysis["bottlenecks"].append({
                            "step": i,
                            "name": step.name or f"Step {i+1}",
                            "duration": job_metrics.processing_duration,
                            "reason": "Significantly slower than average"
                        })
        
        # Calculate efficiency score
        if step_durations:
            total_time = sum(step_durations)
            avg_time = total_time / len(step_durations)
            variance = sum((d - avg_time) ** 2 for d in step_durations) / len(step_durations)
            
            # Lower variance = higher efficiency
            analysis["efficiency_score"] = max(0, 100 - (variance / avg_time * 100))
            
            analysis["resource_usage"] = {
                "peak_memory": max(step_memory) if step_memory else 0,
                "avg_cpu": sum(m.cpu_usage_percent for i, s in enumerate(chain.steps) 
                              for m in [self.metrics_collector.get_job_metrics(f"{chain.chain_id}_step_{i}")] 
                              if m) / len(chain.steps),
                "total_duration": total_time
            }
        
        # Generate recommendations
        if len(analysis["bottlenecks"]) > 0:
            analysis["recommendations"].append("Consider optimizing bottleneck steps")
        
        if analysis["resource_usage"]["peak_memory"] > 1000:  # >1GB
            analysis["recommendations"].append("High memory usage detected - consider memory optimization")
        
        if analysis["efficiency_score"] < 70:
            analysis["recommendations"].append("Chain efficiency is low - review step sequencing")
        
        return analysis
    
    def export_visualization(
        self, 
        viz_data: VisualizationData, 
        format_type: str = "json"
    ) -> Union[str, bytes]:
        """Export visualization in various formats."""
        if format_type.lower() == "json":
            return json.dumps(viz_data.to_dict(), indent=2, default=str)
        elif format_type.lower() == "mermaid":
            return viz_data.to_mermaid()
        elif format_type.lower() == "html":
            return self._generate_html_visualization(viz_data)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    def _generate_html_visualization(self, viz_data: VisualizationData) -> str:
        """Generate HTML visualization with embedded styling."""
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .visualization {{ border: 1px solid #ccc; border-radius: 5px; padding: 20px; }}
        .node {{ 
            display: inline-block; 
            margin: 10px; 
            min-width: 150px; 
            text-align: center;
        }}
        .metadata {{ 
            background: #f8f9fa; 
            padding: 15px; 
            margin-top: 20px; 
            border-radius: 5px; 
        }}
        .timestamp {{ color: #6c757d; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="visualization">
        {nodes_html}
    </div>
    <div class="metadata">
        <h3>Metadata</h3>
        <pre>{metadata}</pre>
        <p class="timestamp">Generated: {timestamp}</p>
    </div>
    <div class="mermaid-diagram">
        <h3>Mermaid Diagram</h3>
        <pre>{mermaid}</pre>
    </div>
</body>
</html>
        """
        
        nodes_html = ""
        for node in viz_data.nodes:
            style_str = "; ".join(f"{k}: {v}" for k, v in node.style.items())
            nodes_html += f'<div class="node" style="{style_str}">{node.label}</div>\n'
        
        return html_template.format(
            title=viz_data.title,
            nodes_html=nodes_html,
            metadata=json.dumps(viz_data.metadata, indent=2, default=str),
            timestamp=viz_data.timestamp.isoformat(),
            mermaid=viz_data.to_mermaid()
        )
    
    def get_cached_visualizations(self) -> List[str]:
        """Get list of cached visualization IDs."""
        with self._lock:
            return list(self._visualization_cache.keys())
    
    def get_visualization(self, viz_id: str) -> Optional[VisualizationData]:
        """Get a cached visualization by ID."""
        with self._lock:
            return self._visualization_cache.get(viz_id)
    
    def clear_cache(self) -> int:
        """Clear visualization cache and return number of items cleared."""
        with self._lock:
            count = len(self._visualization_cache)
            self._visualization_cache.clear()
            return count


# Global visualizer instance
_visualizer_instance: Optional[ChainVisualizer] = None


def get_chain_visualizer() -> ChainVisualizer:
    """Get the global chain visualizer instance."""
    global _visualizer_instance
    if _visualizer_instance is None:
        _visualizer_instance = ChainVisualizer()
    return _visualizer_instance