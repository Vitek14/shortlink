from django.test import TestCase
from django.utils import timezone
from links.models import Link, ClickLog
import datetime


class LinkModelTest(TestCase):
    def setUp(self):
        self.link = Link.objects.create(
            original_url='https://example.com',
            short_code='test123'
        )

    def test_generate_unique_code(self):
        code = Link.generate_unique_code()
        self.assertEqual(len(code), 6)
        # check that the generated code is unique.
        self.assertFalse(Link.objects.filter(short_code=code).exists())

    def test_is_expired(self):
        # link without expiration date
        self.assertFalse(self.link.is_expired())

        # in the past
        self.link.expires_at = timezone.now() - datetime.timedelta(days=1)
        self.assertTrue(self.link.is_expired())

        # in future
        self.link.expires_at = timezone.now() + datetime.timedelta(days=1)
        self.assertFalse(self.link.is_expired())

    def test_increment_clicks(self):
        self.assertEqual(self.link.click_count, 0)
        self.link.increment_clicks()
        self.link.refresh_from_db()
        self.assertEqual(self.link.click_count, 1)

    def test_click_log_creation(self):
        log = ClickLog.objects.create(
            link=self.link,
            ip_address='127.0.0.1',
            user_agent='test-agent'
        )
        self.assertEqual(log.link, self.link)
        self.assertEqual(log.ip_address, '127.0.0.1')
