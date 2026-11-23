from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import dns.flags
import dns.message
import dns.rcode
import dns.rrset

from domain_probes import delegation, parent_sample, result, safe

DOMAIN = "example.test"
EXPECTED = ["vip1.alidns.com", "vip2.alidns.com"]
TIMEOUT = result("unknown", "DNS 查询超时")


class DomainDelegationTest(unittest.TestCase):
    def evaluate(self, *samples):
        with patch("domain_probes.query_parent", return_value=list(zip(("a.test", "b.test"), samples))):
            return delegation(DOMAIN, EXPECTED)

    def test_one_matching_reply_is_enough_when_other_probe_times_out(self):
        for samples in ((TIMEOUT, EXPECTED[::-1]), (EXPECTED, TIMEOUT), (EXPECTED, EXPECTED)):
            with self.subTest(samples=samples):
                check = self.evaluate(*samples)
                self.assertEqual(check["state"], "ok")
                self.assertFalse(check.get("incomplete", False))
                if TIMEOUT in samples:
                    self.assertIn("1/2", check["detail"])
                    self.assertIn("DNS 查询超时", check["detail"])

    def test_all_unavailable_is_unknown_not_missing_delegation(self):
        for samples in ((TIMEOUT, TIMEOUT), ()):
            with self.subTest(samples=samples):
                check = self.evaluate(*samples)
                self.assertEqual(check["state"], "unknown")
                self.assertNotIn("未公布委派", check["detail"])

    def test_conflicting_and_missing_delegations_are_still_bad(self):
        for samples, immediate in (((EXPECTED, ["changed.test"]), False), ((TIMEOUT, []), False), (([], []), True)):
            with self.subTest(samples=samples):
                check = self.evaluate(*samples)
                self.assertEqual((check["state"], check["level"], check["immediate"]), ("bad", 2, immediate))

    def test_authoritative_negative_reply_is_distinct_from_timeout(self):
        reply = dns.message.make_response(dns.message.make_query(DOMAIN, "NS"))
        reply.set_rcode(dns.rcode.NXDOMAIN)
        reply.flags |= dns.flags.AA
        reply.authority.append(dns.rrset.from_text("test.", 300, "IN", "SOA", "ns.test. hostmaster.test. 1 3600 600 86400 300"))
        with patch("domain_probes.direct", return_value=reply):
            self.assertEqual(parent_sample("a.test", DOMAIN, "test"), [])
        with patch("domain_probes.direct", side_effect=dns.exception.Timeout):
            self.assertEqual(safe(parent_sample, "a.test", DOMAIN, "test"), TIMEOUT)
