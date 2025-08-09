"""OAuth2 RFC Compliance Controller

This controller provides endpoints for RFC compliance validation and testing.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from fastapi import Request, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from app.Services.OAuth2RFCComplianceService import OAuth2RFCComplianceService, RFCStandard


class OAuth2RFCComplianceController(BaseController):
    """Controller for OAuth2 RFC compliance validation."""

    def __init__(self) -> None:
        super().__init__()

    async def get_full_compliance_report(
        self,
        request: Request,
        db: Session,
        include_details: bool = Query(True, description="Include detailed validation results")
    ) -> JSONResponse:
        """
        Get comprehensive RFC compliance report.
        
        Args:
            request: FastAPI request object
            db: Database session
            include_details: Whether to include detailed validation results
            
        Returns:
            Complete RFC compliance report
        """
        try:
            compliance_service = OAuth2RFCComplianceService(db)
            
            if include_details:
                report = await compliance_service.validate_full_rfc_compliance()
            else:
                report = await compliance_service.generate_compliance_report_summary()
            
            return JSONResponse(
                status_code=200,
                content={
                    "compliance_report": report,
                    "report_type": "full" if include_details else "summary"
                }
            )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "compliance_validation_failed",
                    "error_description": str(e)
                }
            )

    async def get_rfc_compliance_summary(
        self,
        request: Request,
        db: Session
    ) -> JSONResponse:
        """
        Get summary of RFC compliance status.
        
        Args:
            request: FastAPI request object
            db: Database session
            
        Returns:
            RFC compliance summary
        """
        try:
            compliance_service = OAuth2RFCComplianceService(db)
            summary = await compliance_service.generate_compliance_report_summary()
            
            return JSONResponse(
                status_code=200,
                content=summary
            )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "summary_generation_failed",
                    "error_description": str(e)
                }
            )

    async def validate_specific_rfc(
        self,
        request: Request,
        db: Session,
        rfc: str
    ) -> JSONResponse:
        """
        Validate compliance with a specific RFC standard.
        
        Args:
            request: FastAPI request object
            db: Database session
            rfc: RFC standard to validate (e.g., "RFC 6749")
            
        Returns:
            RFC-specific compliance validation
        """
        try:
            compliance_service = OAuth2RFCComplianceService(db)
            
            # Validate RFC parameter
            if rfc not in compliance_service.implemented_rfcs:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "unsupported_rfc",
                        "error_description": f"RFC {rfc} is not implemented or supported",
                        "supported_rfcs": compliance_service.implemented_rfcs
                    }
                )
            
            validation_result = await compliance_service._validate_rfc_standard(rfc)
            
            return JSONResponse(
                status_code=200,
                content={
                    "rfc_validation": validation_result,
                    "validation_timestamp": validation_result.get("timestamp")
                }
            )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "rfc_validation_failed",
                    "error_description": str(e)
                }
            )

    async def get_implemented_rfcs(
        self,
        request: Request,
        db: Session
    ) -> JSONResponse:
        """
        Get list of implemented RFC standards.
        
        Args:
            request: FastAPI request object
            db: Database session
            
        Returns:
            List of implemented RFCs with descriptions
        """
        try:
            rfc_descriptions = {
                RFCStandard.RFC_6749: "OAuth 2.0 Authorization Framework",
                RFCStandard.RFC_6750: "OAuth 2.0 Bearer Token Usage",
                RFCStandard.RFC_7636: "Proof Key for Code Exchange (PKCE)",
                RFCStandard.RFC_7662: "OAuth 2.0 Token Introspection",
                RFCStandard.RFC_7009: "OAuth 2.0 Token Revocation",
                RFCStandard.RFC_8414: "OAuth 2.0 Authorization Server Metadata",
                RFCStandard.RFC_8628: "OAuth 2.0 Device Authorization Grant",
                RFCStandard.RFC_8693: "OAuth 2.0 Token Exchange",
                RFCStandard.RFC_9126: "OAuth 2.0 Pushed Authorization Requests",
                RFCStandard.RFC_8707: "Resource Indicators for OAuth 2.0",
                RFCStandard.RFC_9449: "OAuth 2.0 Demonstrating Proof-of-Possession",
                RFCStandard.RFC_9396: "OAuth 2.0 Rich Authorization Requests",
                RFCStandard.RFC_8252: "OAuth 2.0 for Native Apps",
                RFCStandard.RFC_9068: "JSON Web Token (JWT) Profile for OAuth 2.0 Access Tokens",
                RFCStandard.RFC_8725: "OAuth 2.0 Security Best Current Practices",
                RFCStandard.RFC_9207: "OAuth 2.0 Authorization Server Issuer Identification",
                RFCStandard.RFC_8705: "OAuth 2.0 Mutual-TLS Client Authentication",
                RFCStandard.RFC_7523: "JSON Web Token (JWT) Profile for OAuth 2.0 Client Authentication and Authorization Grants",
                RFCStandard.RFC_7591: "OAuth 2.0 Dynamic Client Registration Protocol",
                RFCStandard.RFC_7592: "OAuth 2.0 Dynamic Client Registration Management Protocol",
                RFCStandard.RFC_8417: "Security Event Token (SET)"
            }
            
            compliance_service = OAuth2RFCComplianceService(db)
            implemented_rfcs = []
            
            for rfc in compliance_service.implemented_rfcs:
                implemented_rfcs.append({
                    "rfc": rfc,
                    "title": rfc_descriptions.get(rfc, "Unknown RFC"),
                    "validation_endpoint": f"/oauth/compliance/validate/{rfc.replace(' ', '%20')}"
                })
            
            return JSONResponse(
                status_code=200,
                content={
                    "implemented_rfcs": implemented_rfcs,
                    "total_count": len(implemented_rfcs),
                    "compliance_endpoint": "/oauth/compliance/report",
                    "summary_endpoint": "/oauth/compliance/summary"
                }
            )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "rfc_list_failed",
                    "error_description": str(e)
                }
            )

    async def get_compliance_score(
        self,
        request: Request,
        db: Session
    ) -> JSONResponse:
        """
        Get overall compliance score.
        
        Args:
            request: FastAPI request object
            db: Database session
            
        Returns:
            Overall compliance score and level
        """
        try:
            compliance_service = OAuth2RFCComplianceService(db)
            summary = await compliance_service.generate_compliance_report_summary()
            
            return JSONResponse(
                status_code=200,
                content={
                    "overall_score": summary["overall_compliance_score"],
                    "compliance_level": summary["compliance_level"],
                    "total_rfcs": summary["total_rfcs_implemented"],
                    "timestamp": summary["timestamp"]
                }
            )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "score_calculation_failed",
                    "error_description": str(e)
                }
            )

    async def get_compliance_recommendations(
        self,
        request: Request,
        db: Session,
        limit: int = Query(10, description="Maximum number of recommendations to return")
    ) -> JSONResponse:
        """
        Get compliance recommendations.
        
        Args:
            request: FastAPI request object
            db: Database session
            limit: Maximum number of recommendations
            
        Returns:
            List of compliance recommendations
        """
        try:
            compliance_service = OAuth2RFCComplianceService(db)
            full_report = await compliance_service.validate_full_rfc_compliance()
            
            # Get all recommendations
            all_recommendations = full_report.get("recommendations", [])
            critical_issues = full_report.get("errors", [])
            warnings = full_report.get("warnings", [])
            
            # Prioritize recommendations
            prioritized_recommendations = []
            
            # Critical issues first
            for issue in critical_issues[:limit]:
                prioritized_recommendations.append({
                    "type": "critical",
                    "priority": "high",
                    "description": issue,
                    "category": "security"
                })
            
            # Then warnings
            remaining_slots = limit - len(prioritized_recommendations)
            for warning in warnings[:remaining_slots]:
                prioritized_recommendations.append({
                    "type": "warning",
                    "priority": "medium",
                    "description": warning,
                    "category": "best_practice"
                })
            
            # Then general recommendations
            remaining_slots = limit - len(prioritized_recommendations)
            for recommendation in all_recommendations[:remaining_slots]:
                prioritized_recommendations.append({
                    "type": "recommendation",
                    "priority": "low",
                    "description": recommendation,
                    "category": "improvement"
                })
            
            return JSONResponse(
                status_code=200,
                content={
                    "recommendations": prioritized_recommendations,
                    "total_issues": len(critical_issues),
                    "total_warnings": len(warnings),
                    "total_recommendations": len(all_recommendations)
                }
            )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "recommendations_failed",
                    "error_description": str(e)
                }
            )

    async def get_compliance_metrics(
        self,
        request: Request,
        db: Session
    ) -> JSONResponse:
        """
        Get detailed compliance metrics.
        
        Args:
            request: FastAPI request object
            db: Database session
            
        Returns:
            Detailed compliance metrics and analytics
        """
        try:
            compliance_service = OAuth2RFCComplianceService(db)
            full_report = await compliance_service.validate_full_rfc_compliance()
            
            # Calculate metrics
            rfc_scores = []
            total_features_implemented = 0
            total_features_missing = 0
            
            for rfc, result in full_report["compliance_results"].items():
                rfc_scores.append({
                    "rfc": rfc,
                    "score": result.get("score", 0),
                    "level": result.get("compliance_level", "unknown"),
                    "implemented_features": len(result.get("implemented_features", [])),
                    "missing_features": len(result.get("missing_features", []))
                })
                
                total_features_implemented += len(result.get("implemented_features", []))
                total_features_missing += len(result.get("missing_features", []))
            
            # Sort by score
            rfc_scores.sort(key=lambda x: x["score"], reverse=True)
            
            metrics = {
                "overall_score": full_report["overall_score"],
                "compliance_level": full_report["compliance_level"],
                "total_rfcs": len(compliance_service.implemented_rfcs),
                "rfc_scores": rfc_scores,
                "feature_metrics": {
                    "total_implemented": total_features_implemented,
                    "total_missing": total_features_missing,
                    "implementation_rate": round(
                        (total_features_implemented / (total_features_implemented + total_features_missing)) * 100, 2
                    ) if (total_features_implemented + total_features_missing) > 0 else 100
                },
                "compliance_distribution": {
                    "excellent": len([s for s in rfc_scores if s["level"] == "excellent"]),
                    "very_good": len([s for s in rfc_scores if s["level"] == "very_good"]),
                    "good": len([s for s in rfc_scores if s["level"] == "good"]),
                    "fair": len([s for s in rfc_scores if s["level"] == "fair"]),
                    "poor": len([s for s in rfc_scores if s["level"] == "poor"])
                },
                "top_performing_rfcs": rfc_scores[:3],
                "needs_improvement": [s for s in rfc_scores if s["score"] < 80]
            }
            
            return JSONResponse(
                status_code=200,
                content=metrics
            )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "metrics_calculation_failed",
                    "error_description": str(e)
                }
            )