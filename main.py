import logging
import asyncio
from typing import Callable, Iterable
from dataclasses import dataclass
import urllib.parse
from json import JSONDecodeError

from aiohttp import ClientSession, ClientConnectionError


logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger()


@dataclass
class RemoteApiConfig:
    url: str
    extractor: Callable[[dict], str]


ipv4_configs = (
    RemoteApiConfig("https://api.ipify.org?format=json", lambda json_res: json_res["ip"]),
    RemoteApiConfig("https://api.bigdatacloud.net/data/client-ip", lambda json_res: json_res["ipString"]),
    RemoteApiConfig("https://ipv4.monipv6.org/json", lambda json_res: json_res["ipaddress"]),
    RemoteApiConfig("https://ipinfo.io/json", lambda json_res: json_res["ip"]),
)
ipv6_configs = (
    RemoteApiConfig("https://ipv6.monipv6.org/json", lambda json_res: json_res["ipaddress"]),
    RemoteApiConfig("https://api-bdc.net/data/client-ip", lambda json_res: json_res["ipString"]),
    # This one returns a raw value
    # RemoteApiConfig("https://ifconfig.me", lambda r: r),
)


async def aget(sess: ClientSession, url) -> dict:
    try:
        res = await sess.get(url)
    except ClientConnectionError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Unknown request error: {e}"}

    try:
        return await res.json()
    except JSONDecodeError as e:
        return {"error": f"Unable to parse result as JSON: {res.content} ({e})"}
    except Exception as e:
        return {"error": f"Unknown error: {e}"}


async def get_publics_ips(ip_configs: Iterable[RemoteApiConfig]):
    async with ClientSession() as sess:
        coros = (
            aget(sess, config.url) for config in ip_configs
        )
        results: tuple[dict] = await asyncio.gather(*coros)
        result = {
            urllib.parse.urlparse(config.url).hostname: result_dict.get("error") or config.extractor(result_dict)
            for config, result_dict in zip(ip_configs, results)
        }
        return result


async def main():
    log.info("Welcome !")
    ipv4, ipv6 = await asyncio.gather(get_publics_ips(ipv4_configs), get_publics_ips(ipv6_configs))
    log.info(f"Public IPv4: {ipv4}")
    log.info(f"Public IPv6: {ipv6}")


def entrypoint():
    asyncio.run(main())


if __name__ == "__main__":
    """This will be launched when starting script using `python main.py`"""
    entrypoint()
