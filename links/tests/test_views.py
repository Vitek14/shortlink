import json
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from links.models import Link, ClickLog
import datetime
from django.test import override_settings

User = get_user_model()

@override_settings(RATELIMIT_ENABLED=False)
class LinkViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_login(self.user)

        self.link = Link.objects.create(
            original_url='https://example.com',
            short_code='abc123',
            expires_at=timezone.now() + datetime.timedelta(days=1),
            user=self.user
        )
        self.expired_link = Link.objects.create(
            original_url='https://expired.com',
            short_code='expired',
            expires_at=timezone.now() - datetime.timedelta(days=1),
            is_active=True,
            user=self.user
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
        link = Link.objects.get(short_code=resp_data['short_code'])
        self.assertEqual(link.user, self.user)

    def test_create_link_custom_code(self):
        url = reverse('link-create')
        data = {
            'original_url': 'https://custom.example.com',
            'custom_code': 'mycode'
        }
        response = self.client.post(url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['short_code'], 'mycode')
        link = Link.objects.get(short_code='mycode')
        self.assertEqual(link.user, self.user)

    def test_create_link_custom_code_invalid(self):
        url = reverse('link-create')

        data = {
            'original_url': 'https://test.com',
            'custom_code': ''
        }
        response = self.client.post(url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('custom_code must not be empty if provided', response.json()['error'])

        invalid_codes = ['bad code', 'русский', 'code$', 'a'*21]
        for code in invalid_codes:
            data['custom_code'] = code
            response = self.client.post(url, data=json.dumps(data), content_type='application/json')
            self.assertEqual(response.status_code, 400)
            self.assertIn('Invalid custom_code', response.json()['error'])

    def test_create_link_custom_code_conflict(self):
        Link.objects.create(
            original_url='https://taken.com',
            short_code='taken',
            user=self.user
        )
        url = reverse('link-create')
        data = {
            'original_url': 'https://conflict.com',
            'custom_code': 'taken'
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
        self.link.refresh_from_db()
        self.assertEqual(self.link.click_count, 1)
        self.assertTrue(ClickLog.objects.filter(link=self.link).exists())

    def test_redirect_view_expired(self):
        url = reverse('redirect', kwargs={'short_code': 'expired'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 410)
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

    def test_cannot_deactivate_foreign_link(self):
        other_user = User.objects.create_user(username='other', password='otherpass')
        Link.objects.create(
            original_url='https://foreign.com',
            short_code='foreign',
            user=other_user
        )
        url = reverse('link-deactivate', kwargs={'short_code': 'foreign'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        self.assertIn('not the owner', response.json()['error'])

    def test_cannot_delete_foreign_link(self):
        other_user = User.objects.create_user(username='other2', password='otherpass')
        Link.objects.create(
            original_url='https://foreign2.com',
            short_code='foreign2',
            user=other_user
        )
        url = reverse('link-delete', kwargs={'short_code': 'foreign2'})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)
        self.assertIn('not the owner', response.json()['error'])

    def test_unauthorized_create(self):
        self.client.logout()
        url = reverse('link-create')
        data = {'original_url': 'https://shouldfail.com'}
        response = self.client.post(url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 302)

    def test_unauthorized_deactivate(self):
        self.client.logout()
        url = reverse('link-deactivate', kwargs={'short_code': 'abc123'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

    def test_unauthorized_delete(self):
        self.client.logout()
        url = reverse('link-delete', kwargs={'short_code': 'abc123'})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 302)
