import copy as _copy
from hidparser.enums import Collection, ReportFlags, EnumMask, ReportType
from hidparser.UsagePage.UsagePage import UsagePage, Usage, UsageType, UsageRange

from typing import Union, List


class Report:
    def __init__(self, usages: List[Usage], size: int = 0, count: int = 0):
        self.size = size
        self.count = count
        self.usages = usages
        self.usage_switches = []
        self.usage_modifiers = []


class ReportGroup:
    def __init__(self):
        self.inputs = []
        self.outputs = []
        self.features = []


class _CollectionElement:
    def __init__(self, collection: Collection = None, parent = None):
        self.collection = collection
        self.parent = parent
        self.children = []


class DescriptorBuilder:
    def __init__(self):
        self._state_stack = []
        self._items = []
        self._reports = {0: ReportGroup()}
        self._report_group = self._reports[0]
        self._usage_page = None
        self._usages = []

        self.report_size = 0
        self.report_count = 0

        self._collection = _CollectionElement()
        self._current_collection = self._collection

    @property
    def items(self):
        return self._items

    @property
    def reports(self):
        return self._reports

    def add_report(self, report_type: ReportType, flags: Union[ReportFlags, EnumMask, int]):
        usages = []
        while len(usages) < self.report_count:
            usage = self._usages.pop(0) if len(self._usages) > 1 else self._usages[0]
            usages.extend(usage.get_range() if isinstance(usage, UsageRange) else [usage])

        report = Report(usages, self.report_size, self.report_count)

        if report_type is ReportType.input:
            self._report_group.inputs.append(report)
        elif report_type is ReportType.output:
            self._report_group.outputs.append(report)
        elif report_type is ReportType.feature:
            self._report_group.features.append(report)

    def set_report_id(self, report_id: int):
        if report_id in self._reports.keys():
            raise ValueError("Report ID already exists")
        self._reports[report_id] = ReportGroup()
        self._report_group = self._reports[report_id]

    def set_usage_range(self, minimum=None, maximum=None):
        usage = self._usages[len(self._usages)-1] if len(self._usages) else None
        if usage is None or not isinstance(usage, UsageRange):
            usage = UsageRange(self._usage_page)
            self._usages.append(usage)

        if minimum is not None:
            usage.minimum = minimum
        if maximum is not None:
            usage.maximum = maximum

        pass

    def add_usage(self, usage: Union[Usage, int]):
        if isinstance(usage, Usage):
            self._usages.append(usage)
        else:
            usage_page = self._usage_page if (usage & ~0xFFFF) == 0 else UsagePage.find_usage_page((usage & ~0xFFFF) >> 16)
            self._usages.append(usage_page(usage & 0xFFFF))

    def set_usage_page(self, usage_page: UsagePage.__class__):
        self._usage_page = usage_page
        self._usages.clear()

    def push_collection(self, collection: Collection):
        collection_element = _CollectionElement(collection, self._current_collection)
        self._current_collection.children.append(collection_element)
        self._current_collection = collection_element
        return self

    def pop_collection(self):
        if self._current_collection.parent is None:
            raise RuntimeError("Can not pop collection state")
        self._current_collection = self._current_collection.parent
        if self._current_collection.parent is self._collection:
            self._usages.clear()
        return self

    def push(self):
        state = _copy.deepcopy(self.__dict__)
        if "_state_stack" in state.keys():
            del state["_state_stack"]
        self._state_stack.append(state)
        return self

    def pop(self):
        if len(self._state_stack) > 0:
            state = self._state_stack.pop()
            self.__dict__.update(state)
        return self