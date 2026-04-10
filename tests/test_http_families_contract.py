from __future__ import annotations

import iwencai_cli
from tests.helpers import load_spec


def test_runtime_http_endpoints_and_no_proxy_hosts_match_http_families_spec() -> None:
    spec = load_spec("HTTP_FAMILIES.SPEC.yaml")

    assert iwencai_cli.DEFAULT_API_URL == spec["families"]["query2data"]["url"]
    assert iwencai_cli.DEFAULT_SEARCH_API_URL == spec["families"]["comprehensive_search"]["url"]
    assert iwencai_cli.DEFAULT_SIMTRADE_BASE_URL == spec["families"]["simtrade"]["base_url"]
    assert list(iwencai_cli.DEFAULT_NO_PROXY_HOSTS) == spec["runtime_network"]["no_proxy_hosts"]
