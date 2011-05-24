#!/usr/bin/env python
# Copyright (C) 2010 Google Inc. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Chromium Mac implementation of the Port interface."""

import logging
import os
import signal

from webkitpy.layout_tests.port import mac
from webkitpy.layout_tests.port import chromium

from webkitpy.common.system.executive import Executive

_log = logging.getLogger("webkitpy.layout_tests.port.chromium_mac")


class ChromiumMacPort(chromium.ChromiumPort):
    """Chromium Mac implementation of the Port class."""
    SUPPORTED_OS_VERSIONS = ('leopard', 'snowleopard')

    FALLBACK_PATHS = {
        'leopard': ['chromium-mac-leopard', 'chromium-mac-snowleopard', 'chromium-mac', 'chromium',
                    'mac-leopard', 'mac-snowleopard', 'mac'],
        'snowleopard': ['chromium-mac-snowleopard', 'chromium-mac', 'chromium',
                        'mac-snowleopard', 'mac'],
        '': ['chromium-mac', 'chromium', 'mac'],
    }

    def __init__(self, port_name=None, os_version_string=None, rebaselining=False, **kwargs):
        # We're a little generic here because this code is reused by the
        # 'google-chrome' port as well as the 'mock-' and 'dryrun-' ports.
        port_name = port_name or 'chromium-mac'

        if port_name.endswith('-mac'):
            # FIXME: The rebaselining flag is an ugly hack that lets us create an
            # "chromium-mac" port that is not version-specific. It should only be
            # used by rebaseline-chromium-webkit-tests to explicitly put files into
            # the generic directory. In theory we shouldn't need this, because
            # the newest mac port should be using 'chromium-mac' as the baseline
            # directory. However, we also don't have stable SL bots :(
            #
            # When we remove this FIXME, we also need to remove '' as a valid
            # fallback key in self.FALLBACK_PATHS.
            if rebaselining:
                self._version = ''
            else:
                self._version = mac.os_version(os_version_string, self.SUPPORTED_OS_VERSIONS)
                port_name = port_name + '-' + self._version
        else:
            self._version = port_name[port_name.index('-mac-') + 5:]
            assert self._version in self.SUPPORTED_OS_VERSIONS

        chromium.ChromiumPort.__init__(self, port_name=port_name, **kwargs)

    def baseline_path(self):
        if self.version() == 'snowleopard':
            # We treat Snow Leopard as the newest version of mac,
            # so it gets the base dir.
            return self._webkit_baseline_path('chromium-mac')
        return self._webkit_baseline_path(self.name())

    def baseline_search_path(self):
        return map(self._webkit_baseline_path, self.FALLBACK_PATHS[self._version])

    def check_build(self, needs_http):
        result = chromium.ChromiumPort.check_build(self, needs_http)
        result = self._check_wdiff_install() and result
        if not result:
            _log.error('For complete Mac build requirements, please see:')
            _log.error('')
            _log.error('    http://code.google.com/p/chromium/wiki/'
                       'MacBuildInstructions')
        return result

    def default_child_processes(self):
        if self.get_option('worker_model') == 'old-threads':
            # FIXME: we need to run single-threaded for now. See
            # https://bugs.webkit.org/show_bug.cgi?id=38553. Unfortunately this
            # routine is called right before the logger is configured, so if we
            # try to _log.warning(), it gets thrown away.
            import sys
            sys.stderr.write("Defaulting to one child - see https://bugs.webkit.org/show_bug.cgi?id=38553\n")
            return 1

        return chromium.ChromiumPort.default_child_processes(self)

    def default_worker_model(self):
        if self._multiprocessing_is_available:
            return 'processes'
        return 'old-threads'

    def driver_name(self):
        return "DumpRenderTree"

    def test_platform_name(self):
        # We use 'mac' instead of 'chromium-mac'

        # FIXME: Get rid of this method after rebaseline_chromium_webkit_tests dies.
        return 'mac'

    def version(self):
        return self._version

    #
    # PROTECTED METHODS
    #

    def _build_path(self, *comps):
        if self.get_option('build_directory'):
            return self._filesystem.join(self.get_option('build_directory'),
                                         *comps)

        path = self.path_from_chromium_base('xcodebuild', *comps)
        if self._filesystem.exists(path):
            return path
        return self.path_from_webkit_base(
            'Source', 'WebKit', 'chromium', 'xcodebuild', *comps)

    def _check_wdiff_install(self):
        try:
            # We're ignoring the return and always returning True
            self._executive.run_command([self._path_to_wdiff()], error_handler=Executive.ignore_error)
        except OSError:
            _log.warning('wdiff not found. Install using MacPorts or some '
                         'other means')
        return True

    def _lighttpd_path(self, *comps):
        return self.path_from_chromium_base('third_party', 'lighttpd',
                                            'mac', *comps)

    def _path_to_apache(self):
        return '/usr/sbin/httpd'

    def _path_to_apache_config_file(self):
        return self._filesystem.join(self.layout_tests_dir(), 'http', 'conf',
                                     'apache2-httpd.conf')

    def _path_to_lighttpd(self):
        return self._lighttpd_path('bin', 'lighttpd')

    def _path_to_lighttpd_modules(self):
        return self._lighttpd_path('lib')

    def _path_to_lighttpd_php(self):
        return self._lighttpd_path('bin', 'php-cgi')

    def _path_to_driver(self, configuration=None):
        # FIXME: make |configuration| happy with case-sensitive file
        # systems.
        if not configuration:
            configuration = self.get_option('configuration')
        return self._build_path(configuration, self.driver_name() + '.app',
            'Contents', 'MacOS', self.driver_name())

    def _path_to_helper(self):
        binary_name = 'LayoutTestHelper'
        return self._build_path(self.get_option('configuration'), binary_name)

    def _path_to_wdiff(self):
        return 'wdiff'

    def _shut_down_http_server(self, server_pid):
        """Shut down the lighttpd web server. Blocks until it's fully
        shut down.

        Args:
            server_pid: The process ID of the running server.
        """
        # server_pid is not set when "http_server.py stop" is run manually.
        if server_pid is None:
            # TODO(mmoss) This isn't ideal, since it could conflict with
            # lighttpd processes not started by http_server.py,
            # but good enough for now.
            self._executive.kill_all('lighttpd')
            self._executive.kill_all('httpd')
        else:
            try:
                os.kill(server_pid, signal.SIGTERM)
                # TODO(mmoss) Maybe throw in a SIGKILL just to be sure?
            except OSError:
                # Sometimes we get a bad PID (e.g. from a stale httpd.pid
                # file), so if kill fails on the given PID, just try to
                # 'killall' web servers.
                self._shut_down_http_server(None)
