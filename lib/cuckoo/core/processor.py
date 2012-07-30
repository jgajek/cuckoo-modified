# Copyright (C) 2010-2012 Cuckoo Sandbox Developers.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import copy
import logging
import pkgutil

from lib.cuckoo.common.config import Config
from lib.cuckoo.common.abstracts import Processing, Signature
from lib.cuckoo.common.exceptions import CuckooProcessingError
import modules.processing as processing
import modules.signatures as signatures

log = logging.getLogger(__name__)

class Processor:
    """Analysis processor."""

    def __init__(self, analysis_path):
        """@param analysis_path: analysis folder path."""
        self.analysis_path = analysis_path
        self.__populate(processing)
        self.__populate(signatures)

    def __populate(self, modules):
        """Load modules.
        @param modules: modules.
        """
        prefix = modules.__name__ + "."
        for loader, name, ispkg in pkgutil.iter_modules(modules.__path__, prefix):
            if ispkg:
                continue

            __import__(name, globals(), locals(), ["dummy"], -1)

    def run(self):
        """Run all processors and all signatures.
        @return: processing results.
        """
        results = {}
        Processing()

        for module in Processing.__subclasses__():
            self._run_processor(module, results)

        Signature()
        sigs = []

        for signature in Signature.__subclasses__():
            self._run_signature(signature, results, sigs)

        sigs.sort(key=lambda key: key["severity"])
        results["signatures"] = sigs

        return results

    def _run_processor(self, module, results):
        """Run a processor.
        @param module: processor to run.
        @param results: results dict.
        """
        current = module()
        current.set_path(self.analysis_path)
        current.cfg = Config(current.conf_path)

        try:
            results[current.key] = current.run()
            log.debug("Executed processing module \"%s\"" % current.__class__.__name__)
        except NotImplementedError:
            return
        except CuckooProcessingError as e:
            log.warning("The processing module \"%s\" returned the following error: %s" % (current.__class__.__name__, e.message))
        except Exception as e:
            log.warning("Failed to run the processing module \"%s\": %s" % (current.__class__.__name__, e))

    def _run_signature(self, signature, results, sigs):
        """Run a signature.
        @param signature: signature to run.
        @param signs: signature results dict.
        """
        current = signature()
        log.debug("Running signature \"%s\"" % current.name)

        if not current.enabled:
            return

        try:
            if current.run(copy.deepcopy(results)):
                matched = {"name" : current.name,
                           "description" : current.description,
                           "severity" : current.severity,
                           "references" : current.references,
                           "data" : current.data,
                           "alert" : current.alert}
                sigs.append(matched)
                log.debug("Analysis at \"%s\" matched signature \"%s\"" % (self.analysis_path, current.name))
        except NotImplementedError:
            return
        except Exception as e:
            log.warning("Failed to run signature \"%s\": %s" % (current.name, e))
