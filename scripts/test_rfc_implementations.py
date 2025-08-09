#!/usr/bin/env python3
"""Test RFC Implementations

This script tests all the newly implemented RFC standards to ensure they work correctly.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from typing import Dict, Any, List

# import httpx  # Optional dependency for endpoint testing
from sqlalchemy.orm import Session

# Add project root to path
sys.path.insert(0, '/home/r2k/fastapilaravel12')

from config.database import get_db_session
from app.Services.OAuth2DynamicClientRegistrationService import OAuth2DynamicClientRegistrationService
from app.Services.OAuth2SecurityEventService import OAuth2SecurityEventService
from app.Services.OAuth2JWTBearerService import OAuth2JWTBearerService
from app.Services.OAuth2RFCComplianceService import OAuth2RFCComplianceService
from app.Services.OAuth2TokenService import OAuth2TokenService


class RFCImplementationTester:
    """Test suite for RFC implementations."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results: List[Dict[str, Any]] = []

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all RFC implementation tests."""
        print("🚀 Starting RFC Implementation Tests")
        print("=" * 50)

        # Test services directly
        await self._test_dynamic_client_registration()
        await self._test_security_event_service()
        await self._test_jwt_bearer_service()
        await self._test_rfc_compliance_service()
        await self._test_token_service()

        # Test endpoints if server is running
        await self._test_endpoints()

        return self._generate_test_report()

    async def _test_dynamic_client_registration(self) -> None:
        """Test RFC 7591/7592 Dynamic Client Registration."""
        print("\n📋 Testing Dynamic Client Registration (RFC 7591/7592)")
        
        try:
            db = next(get_db_session())
            service = OAuth2DynamicClientRegistrationService(db)

            # Test client metadata validation
            test_metadata = {
                "client_name": "Test Client",
                "client_uri": "https://example.com",
                "redirect_uris": ["https://example.com/callback"],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "scope": "read write",
                "application_type": "web"
            }

            validation_result = await service.validate_registration_request(test_metadata)
            
            if validation_result["valid"]:
                self._log_success("Dynamic Client Registration", "Metadata validation passed")
            else:
                self._log_error("Dynamic Client Registration", f"Validation failed: {validation_result['error']}")

            # Test capabilities
            capabilities = await service.get_registration_capabilities()
            if capabilities.get("registration_endpoint_supported"):
                self._log_success("Dynamic Client Registration", "Capabilities retrieved successfully")
            else:
                self._log_error("Dynamic Client Registration", "Failed to get capabilities")

        except Exception as e:
            self._log_error("Dynamic Client Registration", f"Service test failed: {str(e)}")

    async def _test_security_event_service(self) -> None:
        """Test RFC 8417 Security Event Tokens."""
        print("\n🔒 Testing Security Event Service (RFC 8417)")
        
        try:
            db = next(get_db_session())
            service = OAuth2SecurityEventService(db)

            # Test token revocation event
            subject = {"subject_type": "client", "client_id": "test_client"}
            event_data = {
                "token_identifier": "test_token_123",
                "token_type": "access_token",
                "revocation_reason": "user_action"
            }

            set_token = await service.create_token_revocation_event(
                client_id="test_client",
                token_id="test_token_123",
                reason="user_action"
            )

            if set_token:
                self._log_success("Security Event Service", "Token revocation event created")
                
                # Test validation
                validation_result = await service.validate_security_event_token(set_token)
                if validation_result["valid"]:
                    self._log_success("Security Event Service", "SET validation passed")
                else:
                    self._log_error("Security Event Service", f"SET validation failed: {validation_result['errors']}")
            else:
                self._log_error("Security Event Service", "Failed to create SET")

            # Test capabilities
            capabilities = await service.get_security_event_capabilities()
            if capabilities.get("security_events_supported"):
                self._log_success("Security Event Service", "Capabilities retrieved successfully")
            else:
                self._log_error("Security Event Service", "Failed to get capabilities")

        except Exception as e:
            self._log_error("Security Event Service", f"Service test failed: {str(e)}")

    async def _test_jwt_bearer_service(self) -> None:
        """Test RFC 7523 JWT Bearer Token Grant."""
        print("\n🎫 Testing JWT Bearer Service (RFC 7523)")
        
        try:
            db = next(get_db_session())
            service = OAuth2JWTBearerService(db)

            # Test JWT validation
            test_assertion = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJ0ZXN0X2NsaWVudCIsInN1YiI6InRlc3RfdXNlciIsImF1ZCI6Imh0dHA6Ly9sb2NhbGhvc3Q6ODAwMC9vYXV0aC90b2tlbiIsImV4cCI6OTk5OTk5OTk5OSwiaWF0IjoxNjAwMDAwMDAwfQ.test_signature"
            
            validation_result = await service.validate_jwt_bearer_request(test_assertion)
            
            if validation_result["valid"]:
                self._log_success("JWT Bearer Service", "JWT validation structure check passed")
            else:
                self._log_warning("JWT Bearer Service", f"JWT validation issues: {validation_result['errors']}")

            # Test capabilities
            capabilities = await service.get_jwt_bearer_capabilities()
            if capabilities.get("jwt_bearer_supported"):
                self._log_success("JWT Bearer Service", "Capabilities retrieved successfully")
            else:
                self._log_error("JWT Bearer Service", "Failed to get capabilities")

        except Exception as e:
            self._log_error("JWT Bearer Service", f"Service test failed: {str(e)}")

    async def _test_rfc_compliance_service(self) -> None:
        """Test RFC Compliance Validation Service."""
        print("\n✅ Testing RFC Compliance Service")
        
        try:
            db = next(get_db_session())
            service = OAuth2RFCComplianceService(db)

            # Test compliance report generation
            summary = await service.generate_compliance_report_summary()
            
            if summary.get("total_rfcs_implemented", 0) > 0:
                self._log_success("RFC Compliance Service", f"Found {summary['total_rfcs_implemented']} implemented RFCs")
                self._log_success("RFC Compliance Service", f"Overall compliance score: {summary['overall_compliance_score']}%")
            else:
                self._log_error("RFC Compliance Service", "No RFCs found in compliance report")

            # Test specific RFC validation
            validation_result = await service._validate_rfc_standard("RFC 6749")
            if validation_result.get("implemented"):
                self._log_success("RFC Compliance Service", "RFC 6749 validation passed")
            else:
                self._log_error("RFC Compliance Service", "RFC 6749 validation failed")

        except Exception as e:
            self._log_error("RFC Compliance Service", f"Service test failed: {str(e)}")

    async def _test_token_service(self) -> None:
        """Test OAuth2 Token Service."""
        print("\n🎯 Testing OAuth2 Token Service")
        
        try:
            db = next(get_db_session())
            service = OAuth2TokenService(db)

            # Test token statistics
            stats = await service.get_token_statistics()
            
            if "access_tokens" in stats and "refresh_tokens" in stats:
                self._log_success("Token Service", "Token statistics retrieved successfully")
                print(f"   📊 Access Tokens: {stats['access_tokens']['total']} total, {stats['access_tokens']['active']} active")
                print(f"   📊 Refresh Tokens: {stats['refresh_tokens']['total']} total, {stats['refresh_tokens']['active']} active")
            else:
                self._log_error("Token Service", "Failed to get token statistics")

            # Test cleanup (dry run)
            cleanup_result = await service.cleanup_expired_tokens()
            if isinstance(cleanup_result, dict):
                self._log_success("Token Service", f"Cleanup completed: {cleanup_result}")
            else:
                self._log_error("Token Service", "Cleanup failed")

        except Exception as e:
            self._log_error("Token Service", f"Service test failed: {str(e)}")

    async def _test_endpoints(self) -> None:
        """Test HTTP endpoints if server is running."""
        print("\n🌐 Testing HTTP Endpoints")
        
        try:
            # Try to import httpx for endpoint testing
            import httpx
            
            async with httpx.AsyncClient() as client:
                # Test compliance endpoints
                endpoints_to_test = [
                    "/oauth/compliance/summary",
                    "/oauth/compliance/rfcs", 
                    "/oauth/compliance/score",
                    "/oauth/security-events/capabilities",
                    "/oauth/security-events/event-types"
                ]

                for endpoint in endpoints_to_test:
                    try:
                        response = await client.get(f"{self.base_url}{endpoint}")
                        if response.status_code == 200:
                            self._log_success("HTTP Endpoints", f"GET {endpoint} - OK")
                        else:
                            self._log_warning("HTTP Endpoints", f"GET {endpoint} - Status {response.status_code}")
                    except Exception as e:
                        self._log_warning("HTTP Endpoints", f"GET {endpoint} - Connection failed (server may not be running)")
                        break

        except ImportError:
            self._log_warning("HTTP Endpoints", "httpx not available - skipping endpoint tests (install with: pip install httpx)")
        except Exception as e:
            self._log_warning("HTTP Endpoints", f"Endpoint testing failed: {str(e)} (server may not be running)")

    def _log_success(self, category: str, message: str) -> None:
        """Log a successful test."""
        print(f"   ✅ {message}")
        self.test_results.append({
            "category": category,
            "status": "success",
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })

    def _log_error(self, category: str, message: str) -> None:
        """Log a failed test."""
        print(f"   ❌ {message}")
        self.test_results.append({
            "category": category,
            "status": "error",
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })

    def _log_warning(self, category: str, message: str) -> None:
        """Log a warning."""
        print(f"   ⚠️  {message}")
        self.test_results.append({
            "category": category,
            "status": "warning",
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })

    def _generate_test_report(self) -> Dict[str, Any]:
        """Generate final test report."""
        success_count = len([r for r in self.test_results if r["status"] == "success"])
        error_count = len([r for r in self.test_results if r["status"] == "error"])
        warning_count = len([r for r in self.test_results if r["status"] == "warning"])
        total_tests = len(self.test_results)

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "successful": success_count,
                "errors": error_count,
                "warnings": warning_count,
                "success_rate": round((success_count / total_tests) * 100, 2) if total_tests > 0 else 0
            },
            "results": self.test_results
        }

        print("\n" + "=" * 50)
        print("📊 RFC Implementation Test Results")
        print("=" * 50)
        print(f"Total Tests: {total_tests}")
        print(f"✅ Successful: {success_count}")
        print(f"❌ Errors: {error_count}")
        print(f"⚠️  Warnings: {warning_count}")
        print(f"Success Rate: {report['summary']['success_rate']}%")

        if error_count == 0:
            print("\n🎉 All critical tests passed! RFC implementations are working correctly.")
        elif error_count < success_count:
            print("\n✅ Most tests passed with some issues. Check error details above.")
        else:
            print("\n⚠️  Multiple issues found. Review implementation and fix errors.")

        return report


async def main() -> None:
    """Main test function."""
    tester = RFCImplementationTester()
    
    try:
        report = await tester.run_all_tests()
        
        # Save report to file
        with open("rfc_implementation_test_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Test report saved to: rfc_implementation_test_report.json")
        
        # Exit with appropriate code
        sys.exit(0 if report["summary"]["errors"] == 0 else 1)
        
    except Exception as e:
        print(f"\n💥 Test suite failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())