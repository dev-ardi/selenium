# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.


from importlib import import_module

import pytest

from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.common.options import ArgOptions
from selenium.webdriver.common.proxy import Proxy
from selenium.webdriver.common.proxy import ProxyType
from selenium.webdriver.remote import webdriver
from selenium.webdriver.remote.command import Command
from selenium.webdriver.remote.webdriver import WebDriver


@pytest.mark.parametrize(
    "oss_name, val, w3c_name",
    (
        ("acceptSslCerts", True, "acceptInsecureCerts"),
        ("version", "11", "browserVersion"),
        ("platform", "windows", "platformName"),
    ),
)
def test_non_compliant_w3c_caps_is_deprecated(oss_name, val, w3c_name):
    from selenium.webdriver.remote.webdriver import _make_w3c_caps

    msg = f"{oss_name} is not a w3c capability.  use `{w3c_name}` instead.  This will no longer be converted in 4.7.0"
    with pytest.warns(DeprecationWarning, match=msg):
        _ = _make_w3c_caps({oss_name: val})


def test_converts_proxy_type_value_to_lowercase_for_w3c(mocker):
    mock = mocker.patch("selenium.webdriver.remote.webdriver.WebDriver.execute")
    w3c_caps = {"pageLoadStrategy": "normal", "proxy": {"proxyType": "manual", "httpProxy": "foo"}}
    options = ArgOptions()
    proxy = Proxy({"proxyType": ProxyType.MANUAL, "httpProxy": "foo"})
    options.proxy = proxy
    WebDriver(options=options)
    expected_params = {"capabilities": {"firstMatch": [{}], "alwaysMatch": w3c_caps}}
    mock.assert_called_with(Command.NEW_SESSION, expected_params)


def test_works_as_context_manager(mocker):
    mocker.patch("selenium.webdriver.remote.webdriver.WebDriver.execute")
    quit_ = mocker.patch("selenium.webdriver.remote.webdriver.WebDriver.quit")

    with WebDriver() as driver:
        assert isinstance(driver, WebDriver)

    assert quit_.call_count == 1


@pytest.mark.parametrize("browser_name", ["firefox", "chrome", "ie"])
def test_accepts_firefox_options_to_remote_driver(mocker, browser_name):
    options = import_module(f"selenium.webdriver.{browser_name}.options")
    caps_name = browser_name.upper() if browser_name != "ie" else "INTERNETEXPLORER"
    mock = mocker.patch("selenium.webdriver.remote.webdriver.WebDriver.start_session")

    opts = options.Options()
    opts.add_argument("foo")
    expected_caps = getattr(DesiredCapabilities, caps_name)
    caps = expected_caps.copy()
    expected_caps.update(opts.to_capabilities())

    WebDriver(desired_capabilities=caps, options=opts)
    mock.assert_called_with(expected_caps, None)


def test_always_match_if_2_of_the_same_options():
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.options import Options as ChromeOptions2

    co1 = ChromeOptions()
    co1.add_argument("foo")
    co2 = ChromeOptions2()
    co2.add_argument("bar")

    expected = {
        "capabilities": {
            "alwaysMatch": {
                "browserName": "chrome",
                "pageLoadStrategy": "normal",
            },
            "firstMatch": [
                {"goog:chromeOptions": {"args": ["foo"], "extensions": []}},
                {"goog:chromeOptions": {"args": ["bar"], "extensions": []}},
            ],
        }
    }
    result = webdriver.create_matches([co1, co2])
    assert expected == result


def test_first_match_when_2_different_option_types():
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.firefox.options import Options as FirefoxOptions

    expected = {
        "capabilities": {
            "alwaysMatch": {"pageLoadStrategy": "normal"},
            "firstMatch": [
                {"browserName": "chrome", "goog:chromeOptions": {"extensions": [], "args": []}},
                {
                    "browserName": "firefox",
                    "acceptInsecureCerts": True,
                    "moz:debuggerAddress": True,
                    "moz:firefoxOptions": {"args": ["foo"]},
                },
            ],
        }
    }

    result = webdriver.create_matches([ChromeOptions(), FirefoxOptions()])
    assert expected == result
