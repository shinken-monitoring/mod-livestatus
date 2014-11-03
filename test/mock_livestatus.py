

from functools import partial
import mock


#
from  shinken.modulesctx import modulesctx

# should import the livestatus as a package:
import livestatus # -> livestatus.__file__ should so be '__init__.py' from the livestatus package..

#

old_livestatus_handle_request = livestatus.livestatus_obj.LiveStatus.handle_request
def mocked_livestatus_handle_request(self, request_data):
    '''Implement an extended version of LiveStatus.handle_request where we return
      the response flattened in case it was a LiveStatusListResponse'''
    try:
        response, keepalive = old_livestatus_handle_request(self, request_data)
        if isinstance(response, livestatus.livestatus_response.LiveStatusListResponse):
            response = ''.join(response)
    except livestatus.livestatus_query_error.LiveStatusQueryError as err:
        code, detail = err.args
        response = livestatus.livestatus_response.LiveStatusResponse()
        response.set_error(code, detail)
        if 'fixed16' in request_data:
            response.responseheader = 'fixed16'
        response, keepalive = response.respond()
        response = ''.join(response)
    return response, keepalive
#
# could have also mocked the LiveStatus class itself but then
# it would need to be done when the module is NOT yet imported elsewhere.
# Because there are places/modules (like in shinken_test) where this is done:
# '''
# from shinken.modules.livestatus_broker.livestatus import LiveStatus
# '''
# and so this imported LiveStatus is "unbound" from its module. If the mock.patch
# occurs after such statement then the place where this imported LiveStatus
# name would still use the NOT patched method, simply because it would still
# uses the NOT patched LiveStatus class.
# See below mock_LiveStatus().
#
def mock_livestatus_handle_request(obj):
    '''
    :type obj: Could be a class or a function/method.
    :return: The object with the mocked LiveStatus.handle_request
    '''
    return mock.patch('livestatus.livestatus_obj.LiveStatus.handle_request',
               mocked_livestatus_handle_request)(obj)


def mock_LiveStatus():
    ''' If one wants to mock the LiveStatus class itself. '''
    class LiveStatus(livestatus.LiveStatus):
        mock_livestatus_handle_request = mocked_livestatus_handle_request
    livestatus.LiveStatus = LiveStatus


#
# New LiveStatusClientThread :
#
def mocked_livestatus_client_thread_send_data(self, data):
    # instead of using a socket, simply accumulate the result in a list:
    if not hasattr(self, '_test_buffer_output'):
        self._test_buffer_output = []
    self._test_buffer_output.append(data)


orig_livestatus_client_thread_handle_request = livestatus.livestatus_client_thread.LiveStatusClientThread.handle_request
def mocked_livestatus_client_thread_handle_request(self, response):

    # while the handle_request() from LiveStatus class itself is still mocked because
    # its used by the tests, we need to temporarily replace it the original one:
    prev = self.livestatus.handle_request
    self.livestatus.handle_request = partial(old_livestatus_handle_request, self.livestatus)
    orig_livestatus_client_thread_handle_request(self, response)
    # restore the previous livestatus.handle_request:
    self.livestatus.handle_request = prev
    # then just construct the full response by joining the list which was
    # built within mocked_livestatus_client_thread_send_data
    res = ''.join(self._test_buffer_output)
    del self._test_buffer_output
    return res, None

