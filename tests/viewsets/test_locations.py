# -*- coding: utf-8 -*-
"""
Tests Location viewsets.
"""
from __future__ import unicode_literals

from django.utils import six, timezone

from model_mommy import mommy
from rest_framework.test import APIRequestFactory, force_authenticate
from tests.base import TestBase
from django.contrib.gis.geos import Point

from tasking.common_tags import RADIUS_MISSING, GEOPOINT_MISSING
from tasking.common_tags import GEODETAILS_ONLY
from tasking.models import Location
from tasking.viewsets import LocationViewSet


class TestLocationViewSet(TestBase):
    """
    Test LocationViewSet class.
    """

    def setUp(self):
        super(TestLocationViewSet, self).setUp()
        self.factory = APIRequestFactory()

    def _create_location(self):
        """
        Helper to create a single location
        """
        user = mommy.make('auth.User')

        data = {
            'name': 'Nairobi',
            'country': 'KE',
        }

        view = LocationViewSet.as_view({'post': 'create'})
        request = self.factory.post('/locations', data)
        # Need authenticated user
        force_authenticate(request, user=user)
        response = view(request=request)

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual('Nairobi', response.data['name'])
        self.assertDictContainsSubset(data, response.data)
        return response.data

    def test_create_location(self):
        """
        Test POST /locations adding a new location.
        """
        self._create_location()

    def test_create_with_bad_data(self):
        """
        Test that we get appropriate errors when trying to create an object
        with bad data
        """
        bob_user = mommy.make('auth.User')
        alice_user = mommy.make('auth.User')
        liz_user = mommy.make('auth.User')
        mocked_location_with_shapefile = mommy.make(
            'tasking.Location',
            name='Nairobi',
            _fill_optional=['shapefile'])

        data_missing_radius = dict(
            name='Nairobi',
            geopoint='POINT(30 10)',
            )
        view = LocationViewSet.as_view({'post': 'create'})
        request = self.factory.post('/locations', data_missing_radius)
        # Need authenticated user
        force_authenticate(request, user=bob_user)
        response = view(request=request)

        self.assertEqual(response.status_code, 400)
        self.assertIn('radius', response.data.keys())
        self.assertEqual(RADIUS_MISSING,
                         six.text_type(response.data['radius'][0]))

        data_missing_geopoint = dict(
            name='Montreal',
            radius=45.678)

        view1 = LocationViewSet.as_view({'post': 'create'})
        request1 = self.factory.post('/locations', data_missing_geopoint)
        # Need authenticated user
        force_authenticate(request1, user=liz_user)
        response1 = view1(request=request1)

        self.assertEqual(response1.status_code, 400)
        self.assertIn('geopoint', response1.data.keys())
        self.assertEqual(GEOPOINT_MISSING,
                         six.text_type(response1.data['geopoint'][0]))

        data_shapefile = dict(
            name='Arusha',
            radius=56.6789,
            geopoint='POINT(30 10)',
            shapefile=mocked_location_with_shapefile.shapefile)

        view2 = LocationViewSet.as_view({'post': 'create'})
        request2 = self.factory.post('/locations', data_shapefile)
        # Need authenticated user
        force_authenticate(request2, user=alice_user)
        response2 = view2(request=request2)

        self.assertEqual(response2.status_code, 400)
        self.assertIn('shapefile', response2.data.keys())
        self.assertEqual(GEODETAILS_ONLY,
                         six.text_type(response2.data['shapefile'][0]))

    def test_delete_location(self):
        """
        Test DELETE location.
        """
        user = mommy.make('auth.User')
        location = mommy.make('tasking.Location')

        # assert that location exists
        self.assertTrue(Location.objects.filter(pk=location.id).exists())
        # delete location
        view = LocationViewSet.as_view({'delete': 'destroy'})
        request = self.factory.delete('/locations/{id}'.format(id=location.id))
        force_authenticate(request, user=user)
        response = view(request=request, pk=location.id)
        # assert that location was deleted
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Location.objects.filter(pk=location.id).exists())

    def test_retrieve_location(self):
        """
        Test GET /locations/[pk] return a location matching pk.
        """
        user = mommy.make('auth.User')
        location_data = self._create_location()

        view = LocationViewSet.as_view({'get': 'retrieve'})
        request = self.factory.get(
            '/location/{id}'.format(id=location_data['id']))
        force_authenticate(request, user=user)
        response = view(request=request, pk=location_data['id'])

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, location_data)

    def test_list_locations(self):
        """
        Test GET /locations listing of locations for specific forms.
        """
        user = mommy.make('auth.User')
        location_data = self._create_location()

        view = LocationViewSet.as_view({'get': 'list'})

        request = self.factory.get('/locations')
        force_authenticate(request, user=user)
        response = view(request=request)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data.pop(), location_data)

    def test_update_location(self):
        """
        Test UPDATE location
        """
        user = mommy.make('auth.User')
        location_data = self._create_location()

        data = {
            'name': 'Arusha',
            'country': 'TZ',
        }

        view = LocationViewSet.as_view({'patch': 'partial_update'})
        request = self.factory.patch(
            '/location/{id}'.format(id=location_data['id']), data=data)
        force_authenticate(request, user=user)
        response = view(request=request, pk=location_data['id'])

        self.assertEqual(response.status_code, 200)
        self.assertEqual('Arusha', response.data['name'])
        self.assertEqual('TZ', response.data['country'])

    def test_authentication_required(self):
        """
        Test that authentication is required for all viewset actions
        """
        location_data = self._create_location()
        location1_data = self._create_location()
        location = mommy.make('tasking.Location')

        # test that you need authentication for creating a location
        data = {
            'name': 'Nairobi',
            'country': 'KE',
            }

        view = LocationViewSet.as_view({'post': 'create'})
        request = self.factory.post('/locations', data)

        response = view(request=request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            'Authentication credentials were not provided.',
            six.text_type(response.data['detail']))

        # test that you need authentication for retrieving a location
        view1 = LocationViewSet.as_view({'get': 'retrieve'})
        request1 = self.factory.get(
            '/location/{id}'.format(id=location_data['id']))
        response1 = view1(request=request1, pk=location_data['id'])

        self.assertEqual(response1.status_code, 403)
        self.assertEqual(
            'Authentication credentials were not provided.',
            six.text_type(response1.data['detail']))

        # test that you need authentication for listing a task
        view2 = LocationViewSet.as_view({'get': 'list'})
        request2 = self.factory.get('/locations')
        response2 = view2(request=request2)

        self.assertEqual(response2.status_code, 403)
        self.assertEqual(
            'Authentication credentials were not provided.',
            six.text_type(response2.data['detail']))

        # test that you need authentication for deleting a task
        # assert that location exists
        self.assertTrue(Location.objects.filter(pk=location.id).exists())

        view3 = LocationViewSet.as_view({'delete': 'destroy'})
        request3 = self.factory.delete(
            '/locations/{id}'.format(id=location.id))
        response3 = view3(request=request3, pk=location.id)

        self.assertEqual(response3.status_code, 403)
        self.assertEqual(
            'Authentication credentials were not provided.',
            six.text_type(response3.data['detail']))

        # test that you need authentication for updating a task
        data2 = {
            'name': 'Arusha',
            'country': 'TZ',
        }

        view4 = LocationViewSet.as_view({'patch': 'partial_update'})
        request4 = self.factory.patch(
            '/location/{id}'.format(id=location1_data['id']), data=data2)
        response4 = view4(request=request4, pk=location1_data['id'])

        self.assertEqual(response4.status_code, 403)
        self.assertEqual(
            'Authentication credentials were not provided.',
            six.text_type(response4.data['detail']))