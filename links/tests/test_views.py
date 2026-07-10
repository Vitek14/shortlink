import json
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from links.models import Link, ClickLog
import datetime


class LinkViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.link = Link.objects.create(
            original_url='https://example.com',
            short_code='abc123',
            expires_at=timezone.now() + datetime.timedelta(days=1)
        )
        # helper var with link that expired
        self.expired_link = Link.objects.create(
            original_url='https://expired.com',
            short_code='expired',
            expires_at=timezone.now() - datetime.timedelta(days=1),
            is_active=True
        )

    def test_create_link_auto_code(self):
        url = reverse('link-create')
        data = {'original_url': 'https://new.example.com'}
        response = self.client.post(url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        resp_data = response.json()
        self.assertIn('short_code', resp_data)
        self.assertEqual(resp_data['original_url'], 'https://new.example.com')
        self.assertIsNone(resp_data['expires_at'])
        # link must be created in db
        self.assertTrue(Link.objects.filter(short_code=resp_data['short_code']).exists())

    def test_create_link_custom_code(self):
        url = reverse('link-create')
        data = {
            'original_url': 'https://custom.example.com',
            'custom_code': 'mycode'
        }
        response = self.client.post(url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['short_code'], 'mycode')
        self.assertTrue(Link.objects.filter(short_code='mycode').exists())

    def test_create_link_custom_code_conflict(self):
        url = reverse('link-create')
        data = {
            'original_url': 'https://conflict.com',
            'custom_code': 'abc123'  # уже существует
        }
        response = self.client.post(url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Custom code already taken', response.json()['error'])

    def test_create_link_with_expiration(self):
        url = reverse('link-create')
        future = (timezone.now() + datetime.timedelta(days=10)).isoformat()
        data = {
            'original_url': 'https://future.com',
            'expires_at': future
        }
        response = self.client.post(url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertIsNotNone(response.json()['expires_at'])

    def test_create_link_invalid_expiration(self):
        url = reverse('link-create')
        past = (timezone.now() - datetime.timedelta(days=1)).isoformat()
        data = {
            'original_url': 'https://past.com',
            'expires_at': past
        }
        response = self.client.post(url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Expiration date must be in the future', response.json()['error'])

    def test_redirect_view_success(self):
        url = reverse('redirect', kwargs={'short_code': 'abc123'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, 'https://example.com')
        # Checking the increase in the counter and the creation of the log
        self.link.refresh_from_db()
        self.assertEqual(self.link.click_count, 1)
        self.assertTrue(ClickLog.objects.filter(link=self.link).exists())

    def test_redirect_view_expired(self):
        url = reverse('redirect', kwargs={'short_code': 'expired'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 410)  # Gone
        self.expired_link.refresh_from_db()
        self.assertFalse(self.expired_link.is_active)

    def test_redirect_view_not_found(self):
        url = reverse('redirect', kwargs={'short_code': 'nonexistent'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_link_info_view(self):
        url = reverse('link-info', kwargs={'short_code': 'abc123'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['original_url'], 'https://example.com')
        self.assertEqual(data['short_code'], 'abc123')
        self.assertTrue(data['is_active'])
        self.assertEqual(data['click_count'], 0)

    def test_link_deactivate(self):
        url = reverse('link-deactivate', kwargs={'short_code': 'abc123'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'deactivated')
        self.link.refresh_from_db()
        self.assertFalse(self.link.is_active)

    def test_link_delete(self):
        url = reverse('link-delete', kwargs={'short_code': 'abc123'})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'deleted')
        self.assertFalse(Link.objects.filter(short_code='abc123').exists())
