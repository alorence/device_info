import asyncio
import logging
import urllib.parse
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from json import JSONDecodeError

from aiohttp import ClientConnectionError, ClientResponse, ClientSession

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

log = logging.getLogger()


@dataclass
class RemoteApiConfig:
    url: str
    extractor: Callable[[dict], str] = None

    async def extract_result(self, result: ClientResponse) -> str:
        if self.extractor:
            return self.extractor(await result.json())
        return await result.text()


ipv4_configs = (
    RemoteApiConfig("https://api.ipify.org?format=json", lambda json_res: json_res["ip"]),
    RemoteApiConfig("https://api.bigdatacloud.net/data/client-ip", lambda json_res: json_res["ipString"]),
    RemoteApiConfig("https://ipv4.monipv6.org/json", lambda json_res: json_res["ipaddress"]),
    RemoteApiConfig("https://ipinfo.io/json", lambda json_res: json_res["ip"]),
)
ipv6_configs = (
    RemoteApiConfig("https://ipv6.monipv6.org/json", lambda json_res: json_res["ipaddress"]),
    RemoteApiConfig("https://api-bdc.net/data/client-ip", lambda json_res: json_res["ipString"]),
    RemoteApiConfig("https://ifconfig.me/ip"),
)


async def aget(sess: ClientSession, config: RemoteApiConfig) -> dict:
    try:
        res: ClientResponse = await sess.get(config.url)
    except ClientConnectionError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Unknown request error: {e}"}

    try:
        return {"value": await config.extract_result(res)}
    except JSONDecodeError as e:
        return {"error": f"Unable to parse result as JSON: {res.content} ({e})"}
    except Exception as e:
        return {"error": f"Unknown error: {e}"}


async def get_publics_ips(ip_configs: Iterable[RemoteApiConfig]):
    async with ClientSession() as sess:
        results: tuple[dict] = await asyncio.gather(*(aget(sess, config) for config in ip_configs))
        result = {
            urllib.parse.urlparse(config.url).hostname: result_dict.get("error") or result_dict["value"]
            for config, result_dict in zip(ip_configs, results)
        }
        return result


async def main():
    log.info("Welcome !")
    ipv4, ipv6 = await asyncio.gather(get_publics_ips(ipv4_configs), get_publics_ips(ipv6_configs))
    log.info("Public IPv4: %s", ipv4)
    log.info("Public IPv6: %s", ipv6)


def entrypoint():
    asyncio.run(main())


if __name__ == "__main__":
    """This will be launched when starting script using `python main.py`"""
    entrypoint()
