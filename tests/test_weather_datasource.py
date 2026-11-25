"""Verify that weather failures preserve behavior and omit request details."""

from traceback import format_exception
from unittest.mock import Mock

import pytest
from requests.exceptions import HTTPError

from twinkly_wall.datasources import weather


@pytest.mark.parametrize("with_stale_cache", [False, True])
def test_weather_request_failure_omits_coordinates(monkeypatch, caplog, with_stale_cache):
    latitude, longitude = 12.345678, -98.765432
    datasource = weather.WeatherDataSource(latitude, longitude, cache_duration=0)
    failed_response = Mock()
    failed_response.raise_for_status.side_effect = HTTPError(
        f"Request failed for https://weather.example/?latitude={latitude}&longitude={longitude}"
    )
    response = Mock()
    response.json.return_value = {"current": {"temperature_2m": 7}}
    requests_get = Mock(
        side_effect=[response, failed_response] if with_stale_cache else [failed_response]
    )
    monkeypatch.setattr(weather.requests, "get", requests_get)

    error_text = ""
    if with_stale_cache:
        cached = datasource.get_weather()
        assert cached.temperature == 7
        assert datasource.get_weather() is cached
    else:
        with pytest.raises(
            weather.WeatherError, match=r"Failed to fetch weather \(HTTPError\)"
        ) as error:
            datasource.get_weather()
        error_text = "".join(format_exception(error.value))

    for call in requests_get.call_args_list:
        params = call.kwargs["params"]
        assert (params["latitude"], params["longitude"]) == (latitude, longitude)
    assert "Weather fetch failed: Failed to fetch weather (HTTPError)" in caplog.messages
    for value in (str(latitude), str(longitude), "https://weather.example/"):
        assert value not in caplog.text
        assert value not in error_text
