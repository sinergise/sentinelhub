"""
Implementation of Sentinel Hub Stat API interface
"""
from .constants import MimeType, RequestType
from .data_collections import DataCollection
from .download import DownloadRequest
from .download.sentinelhub_stat_client import SentinelHubStatDownloadClient
from .data_request import DataRequest
from .sentinelhub_request import SentinelHubRequest, InputDataDict
from .geometry import Geometry, BBox
from .time_utils import parse_time_interval, serialize_time


class SentinelHubStat(DataRequest):

    def __init__(self, aggregation, input_data, bbox=None, geometry=None, calculations=None, **kwargs):

        # For now service won't work without this
        for input_data_payload in input_data:
            if 'dataFilter' not in input_data_payload:
                input_data_payload['dataFilter'] = {}

        self.payload = self.body(
            request_bounds=SentinelHubRequest.bounds(bbox=bbox, geometry=geometry),
            request_data=input_data,
            aggregation=aggregation,
            calculations=calculations
        )

        super().__init__(SentinelHubStatDownloadClient, **kwargs)

    def create_request(self):
        """ Prepares a download request
        """
        headers = {'content-type': MimeType.JSON.get_string(), 'accept': MimeType.JSON.get_string()}

        self.download_list = [DownloadRequest(
            request_type=RequestType.POST,
            url=self._get_request_url(),
            post_values=self.payload,
            data_folder=self.data_folder,
            save_response=bool(self.data_folder),
            data_type=MimeType.JSON,
            headers=headers,
            use_session=True
        )]

    def body(self, request_bounds, request_data, aggregation, calculations):
        if calculations is None:
            calculations = {
                'default': {}
            }

        return {
            'input': {
                'bounds': request_bounds,
                'data': request_data
            },
            'aggregation': aggregation,
            'calculations': calculations
        }

    @staticmethod
    def aggregation(evalscript, time_interval, aggregation_interval, size=None, resolution=None, **kwargs):
        start_time, end_time = serialize_time(parse_time_interval(time_interval, allow_undefined=True), use_tz=True)

        payload = {
            'evalscript': evalscript,
            'timeRange': {
                'from': start_time,
                'to': end_time
            },
            'aggregationInterval': {
                'of': aggregation_interval
            },
            **kwargs
        }

        if size:
            payload['width'], payload['height'] = size
        if resolution:
            payload['resx'], payload['resy'] = resolution

        return payload

    @staticmethod
    def calculations():
        raise NotImplementedError

    def _get_request_url(self):
        data_collection_urls = tuple({
            input_data_dict.service_url for input_data_dict in self.payload['input']['data']
            if isinstance(input_data_dict, InputDataDict) and input_data_dict.service_url is not None
        })
        if len(data_collection_urls) > 1:
            raise ValueError(f'Given data collections are restricted to different services: {data_collection_urls}\n'
                             f'Try defining data collections without these restrictions')

        base_url = data_collection_urls[0] if data_collection_urls else self.config.sh_base_url
        return f'{base_url}/api/v1/statistics'