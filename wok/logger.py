###############################################################################
#
#    Copyright 2009-2013, Universitat Pompeu Fabra
#
#    This file is part of Wok.
#
#    Wok is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Wok is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses
#
###############################################################################

import logging

from wok.config.data import Data

_DEFAULT_FORMAT = "%(asctime)s %(name)-20s [%(levelname)-5s] %(message)s"
#_DEFAULT_FORMAT = "%(asctime)s %(module)s %(funcName)s %(name)s %(levelname) -5s : %(message)s"

_DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"
#_DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"

_log_level_map = {
	"debug" : logging.DEBUG,
	"info" : logging.INFO,
	"warn" : logging.WARN,
	"error" : logging.ERROR,
	"critical" : logging.CRITICAL,
	"notset" : logging.NOTSET }

_initialized = False

def initialize(conf=None, format=None, datefmt=None):
	"""
	Initialize the logging system.

	If conf is a dictionary then the parameters considered for configuration are:
	  - format: Logger format
	  - datefmt: Date format
	  - loggers: list of tuples (name, conf) to configure loggers

	If conf is a list then only the loggers are configured.

	If conf is an string then the default logger is configured for the logging level.
	"""

	global _initialized

	if conf is None:
		conf = Data.element()
	elif not isinstance(conf, basestring):
		conf = Data.create(conf)

	if Data.is_list(conf):
		loggers_conf = conf
		conf = Data.element()
	elif Data.is_element(conf):
		loggers_conf = conf.get("loggers", default=Data.list)
	elif isinstance(conf, basestring):
		loggers_conf = Data.list([["", conf]])
		conf = Data.element()

	format = format or conf.get("format", _DEFAULT_FORMAT)
	datefmt = datefmt or conf.get("datefmt", _DEFAULT_DATEFMT)

	logging.basicConfig(format=format, datefmt=datefmt)

	for (log_name, log_conf) in loggers_conf:
		init_logger(log_name, conf=log_conf)

	_initialized = True

def get_level(level):
	return _log_level_map.get(level.lower(), "notset")

def get_logger(name="", level=None, conf=None):
	"""
	Returns a logger.

	* Configuration parameters:

	- name: Logger name
	- level: Logging level: debug, info, warn, error, critical, notset
	- conf: Data.element with logger configuration parameters: level, handlers
	"""

	if not _initialized:
		initialize(conf)

	logger = logging.getLogger(name)

	if conf is not None:
		init_logger(logger, conf)

	if level is not None:
		logger.setLevel(get_level(level))

	return logger

def init_logger(logger, conf):
	if isinstance(logger, basestring):
		logger = get_logger(logger)

	if isinstance(conf, basestring):
		conf = Data.element(dict(level=conf))
	else:
		conf = Data.create(conf)

	level = conf.get("level")
	if level is not None:
		logger.setLevel(get_level(level))

	handlers_conf = conf.get("handlers", default=Data.list)
	if Data.is_element(handlers_conf):
		handlers_conf = Data.list([handlers_conf])

	for index, handler_conf in enumerate(handlers_conf):
		handler = get_handler(logger, handler_conf)
		logger.addHandler(handler)

def get_handler(logger, conf):
	if not Data.is_element(conf):
		logger.error("Malformed log handler:\n{1}".format(repr(conf)))
		return

	type = conf.get("type")
	if type is None or not isinstance(type, basestring) or type.lower() != "smtp":
		logger.error("Unknown or unsupported handler type: {0}\n{1}".format(type, repr(conf)))
		return

	handler = get_smtp_handler(conf)

	return handler

def get_smtp_handler(conf):
	_log = logging.getLogger(__name__)
	mf = conf.missing_fields(["host", "user", "from", "to", "subject"])
	if len(mf) != 0:
		_log.error("The following fields for the handler are missing: {0}\n{1}".format(", ".join(mf), repr(conf)))
		return

	mailhost = conf.get("host")
	port = conf.get("port")
	if port is not None:
		mailhost = (mailhost, port)

	credentials = conf.get("user")
	passwd = conf.get("pass")
	if passwd is not None:
		credentials = (credentials, passwd)

	fromaddr = conf.get("from")
	toaddr = conf.get("to")
	subject = conf.get("subject")

	handler = logging.handlers.SMTPHandler(mailhost, fromaddr, toaddr, subject, credentials, tuple())

	level = conf.get("level")
	if level is not None:
		handler.setLevel(get_level(level))

	format = conf.get("format")
	if format is not None:
		if isinstance(format, DataList):
			format = "".join(format.to_native())
		handler.setFormatter(logging.Formatter(format))

	return handler