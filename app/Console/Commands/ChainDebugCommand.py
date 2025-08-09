"""
Chain Debugging and Visualization CLI Command
"""
from __future__ import annotations

import json
import argparse
from typing import Dict, Any, Optional
from datetime import datetime

from app.Console.Command import Command
from app.Jobs.ChainRegistry import ChainRegistry
from app.Jobs.ChainVisualizer import get_chain_visualizer, VisualizationType
from app.Jobs.ChainMonitor import get_chain_monitor
from app.Jobs.MetricsCollector import get_metrics_collector
from app.Jobs.RetryManager import get_retry_manager


class ChainDebugCommand(Command):
    """
    Debug and visualize job chains.
    
    Usage:
        python manage.py chain:debug [chain_id] [options]
    """
    
    signature = "chain:debug {chain_id?} {--list} {--visualize=} {--export=} {--performance} {--health} {--metrics} {--retry-info}"
    description = "Debug and visualize job chains with comprehensive analysis"
    
    def __init__(self):
        super().__init__()
        self.registry = ChainRegistry.get_instance()
        self.visualizer = get_chain_visualizer()
        self.monitor = get_chain_monitor()
        self.metrics_collector = get_metrics_collector()
        self.retry_manager = get_retry_manager()
    
    def handle(self) -> None:
        """Handle the command execution."""
        chain_id = self.argument('chain_id')
        
        # List all chains if no specific chain ID provided
        if self.option('list') or not chain_id:
            self.list_chains()
            return
        
        # Get specific chain
        chain = self.registry.get_chain(chain_id)
        if not chain:
            self.error(f"Chain '{chain_id}' not found")
            return
        
        self.info(f"Debugging chain: {chain.name} (ID: {chain_id})")
        self.line("")
        
        # Show basic chain info
        self.show_chain_info(chain_id, chain)
        
        # Show performance analysis if requested
        if self.option('performance'):
            self.line("")
            self.show_performance_analysis(chain_id, chain)
        
        # Show health checks if requested
        if self.option('health'):
            self.line("")
            self.show_health_checks()
        
        # Show metrics if requested
        if self.option('metrics'):
            self.line("")
            self.show_metrics(chain_id)
        
        # Show retry information if requested
        if self.option('retry-info'):
            self.line("")
            self.show_retry_info(chain_id, chain)
        
        # Create visualization if requested
        viz_type = self.option('visualize')
        if viz_type:
            self.line("")
            self.create_visualization(chain_id, viz_type)
    
    def list_chains(self) -> None:
        """List all active chains."""
        self.info("Active Job Chains:")
        self.line("")
        
        active_chains = self.registry.get_active_chains()
        
        if not active_chains:
            self.comment("No active chains found")
            return
        
        headers = ["Chain ID", "Name", "Status", "Steps", "Current"]
        rows = []
        
        for chain_id, chain in active_chains.items():
            rows.append([
                chain_id[:8] + "..." if len(chain_id) > 11 else chain_id,
                chain.name[:20] + "..." if len(chain.name) > 23 else chain.name,
                chain.status.value,
                str(len(chain.steps)),
                f"{chain.current_step}/{len(chain.steps)}"
            ])
        
        self.table(headers, rows)
        
        self.line("")
        self.comment(f"Total active chains: {len(active_chains)}")
        
        # Show registry stats
        stats = self.registry.get_stats()
        self.comment(f"Registry stats: {stats['completed']} completed, {stats['failed']} failed")
    
    def show_chain_info(self, chain_id: str, chain: Any) -> None:
        """Show detailed chain information."""
        self.info("Chain Information:")
        
        info_data = [
            ["Chain ID", chain_id],
            ["Name", chain.name],
            ["Status", chain.status.value],
            ["Total Steps", str(len(chain.steps))],
            ["Current Step", f"{chain.current_step}/{len(chain.steps)}"],
            ["Created At", "N/A"],  # Would need to track creation time
        ]
        
        self.table(["Property", "Value"], info_data)
        
        # Show step details
        if chain.steps:
            self.line("")
            self.info("Chain Steps:")
            
            step_headers = ["#", "Name", "Job Type", "Status", "Delay", "Options"]
            step_rows = []
            
            for i, step in enumerate(chain.steps):
                status = self._get_step_status(chain, i)
                options = []
                if step.retry_on_failure:
                    options.append("retry")
                if step.continue_on_failure:
                    options.append("continue")
                
                step_rows.append([
                    str(i + 1),
                    step.name or f"Step {i+1}",
                    type(step.job).__name__,
                    status,
                    f"{step.delay}s" if step.delay > 0 else "none",
                    ", ".join(options) if options else "none"
                ])
            
            self.table(step_headers, step_rows)
    
    def show_performance_analysis(self, chain_id: str, chain: Any) -> None:
        """Show performance analysis."""
        self.info("Performance Analysis:")
        
        analysis = self.visualizer._analyze_chain_performance(chain)
        
        # Show efficiency score
        score_color = "green" if analysis["efficiency_score"] > 80 else "yellow" if analysis["efficiency_score"] > 60 else "red"
        self.line(f"<fg={score_color}>Efficiency Score: {analysis['efficiency_score']:.1f}/100</>")
        
        # Show resource usage
        resources = analysis["resource_usage"]
        self.line(f"Peak Memory: {resources['peak_memory']:.1f} MB")
        self.line(f"Average CPU: {resources['avg_cpu']:.1f}%")
        self.line(f"Total Duration: {resources['total_duration']:.2f}s")
        
        # Show bottlenecks
        if analysis["bottlenecks"]:
            self.line("")
            self.warn("Detected Bottlenecks:")
            for bottleneck in analysis["bottlenecks"]:
                self.line(f"  • Step {bottleneck['step'] + 1}: {bottleneck['name']}")
                self.line(f"    Duration: {bottleneck['duration']:.2f}s")
                self.line(f"    Reason: {bottleneck['reason']}")
        
        # Show recommendations
        if analysis["recommendations"]:
            self.line("")
            self.info("Recommendations:")
            for recommendation in analysis["recommendations"]:
                self.line(f"  • {recommendation}")
    
    def show_health_checks(self) -> None:
        """Show system health checks."""
        self.info("System Health Checks:")
        
        health_info = self.monitor.get_current_health()
        
        # Overall status
        status_color = {
            "healthy": "green",
            "warning": "yellow", 
            "critical": "red",
            "unknown": "gray"
        }.get(health_info["overall_status"], "gray")
        
        self.line(f"Overall Status: <fg={status_color}>{health_info['overall_status'].upper()}</>")
        
        # Individual checks
        self.line("")
        check_headers = ["Check", "Status", "Message", "Duration"]
        check_rows = []
        
        for check in health_info["checks"]:
            status_color = {
                "healthy": "green",
                "warning": "yellow",
                "critical": "red", 
                "unknown": "gray"
            }.get(check["status"], "gray")
            
            check_rows.append([
                check.get("check_name", "Unknown"),
                f"<fg={status_color}>{check['status'].upper()}</>",
                check["message"][:50] + "..." if len(check["message"]) > 53 else check["message"],
                f"{check['check_duration']:.3f}s"
            ])
        
        self.table(check_headers, check_rows)
        
        # Summary
        summary = health_info["summary"]
        self.line("")
        self.comment(f"Summary: {summary['healthy']} healthy, {summary['warning']} warnings, {summary['critical']} critical")
    
    def show_metrics(self, chain_id: str) -> None:
        """Show metrics for the chain."""
        self.info("Chain Metrics:")
        
        # Get overall metrics
        overall_metrics = self.metrics_collector.get_overall_metrics(hours=24)
        
        if overall_metrics.get("job_count", 0) == 0:
            self.comment("No metrics available")
            return
        
        # Basic metrics
        metrics_data = [
            ["Total Jobs", str(overall_metrics.get("job_count", 0))],
            ["Success Count", str(overall_metrics.get("success_count", 0))],
            ["Failure Count", str(overall_metrics.get("failure_count", 0))],
            ["Success Rate", f"{overall_metrics.get('success_rate', 0):.1f}%"],
            ["Error Rate", f"{overall_metrics.get('error_rate', 0):.1f}%"],
            ["Retry Rate", f"{overall_metrics.get('retry_rate', 0):.1f}%"]
        ]
        
        if "avg_processing_duration" in overall_metrics:
            metrics_data.extend([
                ["Avg Duration", f"{overall_metrics['avg_processing_duration']:.2f}s"],
                ["P95 Duration", f"{overall_metrics.get('p95_processing_duration', 0):.2f}s"],
                ["Max Duration", f"{overall_metrics.get('max_processing_duration', 0):.2f}s"]
            ])
        
        self.table(["Metric", "Value"], metrics_data)
        
        # Top errors
        if overall_metrics.get("top_errors"):
            self.line("")
            self.info("Top Errors:")
            for error in overall_metrics["top_errors"][:5]:
                self.line(f"  • {error['error_type']}: {error['count']} occurrences")
    
    def show_retry_info(self, chain_id: str, chain: Any) -> None:
        """Show retry information for chain steps."""
        self.info("Retry Information:")
        
        has_retries = False
        
        for i, step in enumerate(chain.steps):
            step_job_id = f"{chain_id}_step_{i}"
            retry_info = self.retry_manager.get_retry_info(step_job_id)
            
            if retry_info:
                has_retries = True
                self.line(f"\nStep {i+1} ({step.name or 'Unnamed'}):")
                self.line(f"  Max Retries: {retry_info.max_retries}")
                self.line(f"  Current Attempt: {retry_info.current_attempt}")
                self.line(f"  Total Attempts: {len(retry_info.attempts)}")
                self.line(f"  Is Exhausted: {'Yes' if retry_info.is_exhausted else 'No'}")
                
                if retry_info.attempts:
                    self.line("  Retry History:")
                    for attempt in retry_info.attempts[-3:]:  # Show last 3 attempts
                        self.line(f"    • Attempt {attempt.attempt_number}: {attempt.error_type}")
                        self.line(f"      Time: {attempt.timestamp.strftime('%H:%M:%S')}")
                        self.line(f"      Delay: {attempt.delay_seconds:.2f}s")
        
        if not has_retries:
            self.comment("No retry information available for this chain")
    
    def create_visualization(self, chain_id: str, viz_type: str) -> None:
        """Create and export visualization."""
        self.info(f"Creating {viz_type} visualization...")
        
        try:
            visualization_type = VisualizationType(viz_type)
        except ValueError:
            self.error(f"Invalid visualization type. Available types: {[vt.value for vt in VisualizationType]}")
            return
        
        viz_data = self.visualizer.visualize_chain(chain_id, visualization_type)
        if not viz_data:
            self.error("Failed to create visualization")
            return
        
        export_format = self.option('export', 'mermaid')
        
        try:
            exported_data = self.visualizer.export_visualization(viz_data, export_format)
            
            # Save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chain_{chain_id[:8]}_{viz_type}_{timestamp}.{export_format}"
            
            with open(filename, 'w') as f:
                f.write(exported_data)
            
            self.info(f"Visualization exported to: {filename}")
            
            # Show preview for Mermaid
            if export_format == 'mermaid':
                self.line("")
                self.info("Mermaid Diagram Preview:")
                self.line(exported_data)
        
        except Exception as e:
            self.error(f"Failed to export visualization: {str(e)}")
    
    def _get_step_status(self, chain: Any, step_index: int) -> str:
        """Get the current status of a chain step."""
        from app.Jobs.Chain import ChainStatus
        
        if step_index < chain.current_step:
            return "<fg=green>completed</>"
        elif step_index == chain.current_step and chain.status == ChainStatus.RUNNING:
            return "<fg=blue>running</>"
        elif step_index == chain.current_step and chain.status == ChainStatus.FAILED:
            return "<fg=red>failed</>"
        else:
            return "<fg=gray>pending</>"


# Register the command
def register_command():
    return ChainDebugCommand()