import logging
import platform
import sys
import time
from urllib.parse import urlparse

from dns import resolver

from ..network.ban_ips import BAN_IPS
from ..utils.dns_utils import get_status_code_from_request, configure_linux_dns, configure_windows_dns, \
    configure_mac_dns


def test_dns_with_custom_ip(url: str, dns_ip: str) -> (str, float):
    """
    Tests the DNS configuration by sending a request to a specific URL using a custom DNS IP.
    Returns the number of records found and the response time.
    """
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname

    start_time = time.perf_counter()

    dns_failure_time = 0.0

    try:
        custom_resolver = resolver.Resolver()
        custom_resolver.nameservers = [dns_ip]
        custom_resolver.timeout = 5
        custom_resolver.lifetime = 5

        result = custom_resolver.resolve(hostname, "A", raise_on_no_answer=False)
        response_time = time.perf_counter() - start_time
        ip = result.rrset._rdata_repr()
        ip = ip[ip.find("<") + 1: ip.find(">")]

        if ip in BAN_IPS:
            return 451, dns_failure_time

        status_code = get_status_code_from_request(ip)

        if status_code == 403:
            return 403, dns_failure_time

        return 200, response_time

    except (
            resolver.NoAnswer,
            resolver.NXDOMAIN,
            resolver.LifetimeTimeout,
            resolver.NoNameservers,
    ):
        return 500, dns_failure_time


def set_dns(preferred_dns: str, alternative_dns: str | None = None) -> None:
    system_platform = platform.system()
    configurators = {
        "Linux": configure_linux_dns,
        "Windows": configure_windows_dns,
        "Darwin": configure_mac_dns,
    }

    if configurator := configurators.get(system_platform):
        configurator(preferred_dns, alternative_dns)
    else:
        logging.error(f"Unsupported platform: {system_platform}")
        sys.exit(1)


def test_dns(dns, url):
    dns_name = dns["name"]
    preferred_dns = dns["preferred"]
    alternative_dns = dns["alternative"]

    status, response_time = test_dns_with_custom_ip(url, preferred_dns)
    status_message = "[green]Success[/green]" if status == 200 else "[red]Failed[/red]"
    response_time_display = (
        f"{response_time:.4f}" if response_time < float("inf") else "N/A"
    )

    return (
        dns_name,
        preferred_dns,
        alternative_dns,
        status_message,
        response_time_display,
    )
