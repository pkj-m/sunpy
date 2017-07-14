# -*- coding: utf-8 -*-
from __future__ import absolute_import, division
import datetime

import numpy as np
import astropy.units as u
from astropy.time import Time
from astropy.coordinates import SkyCoord, Angle, get_body_barycentric,\
                                PrecessedGeocentric, AltAz
from astropy.coordinates.representation import CartesianRepresentation

from sunpy.time import parse_time

from .frames import HeliographicStonyhurst as HGS

__all__ = ['get_earth', 'get_sun_B0', 'get_sun_P', 'get_sun_orientation']


def get_earth(time='now'):
    """
    Return a SkyCoord for the location of the Earth at a specified time in the
    HeliographicStonyhurst frame.  The longitude will be 0 by definition.

    Parameters
    ----------
    time : various
        Time to use in a parse_time-compatible format

    Returns
    -------
    out : `~astropy.coordinates.SkyCoord`
        SkyCoord for the location of the Earth in the HeliographicStonyhurst frame
    """
    obstime = Time(parse_time(time))

    earth_icrs = get_body_barycentric('earth', obstime)
    earth = SkyCoord(earth_icrs, frame='icrs', obstime=obstime).transform_to(HGS)

    # Explicitly set the longitude to 0
    earth = SkyCoord(0*u.deg, earth.lat, earth.radius, frame=earth)

    return earth


def get_sun_B0(time='now'):
    """
    Return the B0 angle for the Sun at a specified time, which is the heliographic latitude of the
    Sun-disk center as seen from Earth.  The range of B0 is +/-7.23 degrees.

    Parameters
    ----------
    time : various
        Time to use in a parse_time-compatible format

    Returns
    -------
    out : `~astropy.coordinates.Angle`
        The position angle
    """
    return Angle(get_earth(time).lat)


def get_sun_P(time='now'):
    """
    Return the position (P) angle for the Sun at a specified time, which is the angle between
    geocentric north and solar north as seen from Earth, measured eastward from geocentric north.
    The range of P is +/-26.3 degrees.

    Parameters
    ----------
    time : various
        Time to use in a parse_time-compatible format

    Returns
    -------
    out : `~astropy.coordinates.Angle`
        The position angle
    """
    obstime = Time(parse_time(time))

    geocentric = PrecessedGeocentric(equinox=obstime, obstime=obstime)

    return _sun_north_angle_to_z(geocentric)


def get_sun_orientation(location, time='now'):
    """
    Return the orientation angle for the Sun from a specified Earth location and time.  The
    orientation angle is the angle between local zenith and solar north, measured eastward from
    local zenith.

    Parameters
    ----------
    location : `~astropy.coordinates.EarthLocation`
        Observer location on Earth
    time : various
        Time to use in a parse_time-compatible format

    Returns
    -------
    out : `~astropy.coordinates.Angle`
        The orientation of the Sun
    """
    obstime = Time(parse_time(time))

    local_frame = AltAz(obstime=obstime, location=location)

    return _sun_north_angle_to_z(local_frame)


def _sun_north_angle_to_z(frame):
    """
    Return the angle between solar north and the Z axis of the provided frame's coordinate system
    and observation time.
    """
    # Find the Sun center and Sun north in HGS at the frame's observation time
    sun_center = SkyCoord(0*u.deg, 0*u.deg, 0*u.km, frame=HGS, obstime=frame.obstime)
    sun_north = SkyCoord(0*u.deg, 90*u.deg, 690000*u.km, frame=HGS, obstime=frame.obstime)

    # Find the Sun center and Sun north in the frame's coordinate system
    sky_normal = sun_center.transform_to(frame).data.to_cartesian()
    sun_north = sun_north.transform_to(frame).data.to_cartesian()

    # Use cross products to obtain the sky projections of the two vectors (rotated by 90 deg)
    sun_north_in_sky = sun_north.cross(sky_normal)
    z_in_sky = CartesianRepresentation(0, 0, 1).cross(sky_normal)

    # Normalize directional vectors
    sky_normal /= sky_normal.norm()
    sun_north_in_sky /= sun_north_in_sky.norm()
    z_in_sky /= z_in_sky.norm()

    # Calculate the signed angle between the two projected vectors
    cos_theta = sun_north_in_sky.dot(z_in_sky)
    sin_theta = sun_north_in_sky.cross(z_in_sky).dot(sky_normal)
    angle = np.arctan2(sin_theta, cos_theta).to('deg')

    return Angle(angle)
