from __future__ import annotations

import ctypes
import ctypes.util
import queue
import time
from dataclasses import dataclass


CFTypeRef = ctypes.c_void_p
IOHIDManagerRef = ctypes.c_void_p
IOHIDDeviceRef = ctypes.c_void_p
IOOptionBits = ctypes.c_uint32
IOReturn = ctypes.c_int32

K_CF_STRING_ENCODING_UTF8 = 0x08000100
K_CF_NUMBER_SINT32_TYPE = 3
K_IOHID_REPORT_TYPE_INPUT = 0
K_IOHID_REPORT_TYPE_OUTPUT = 1
K_IOHID_REPORT_TYPE_FEATURE = 2
K_IOHID_OPTIONS_TYPE_NONE = 0
K_IOHID_OPTIONS_TYPE_SEIZE_DEVICE = 1


class MacHIDError(RuntimeError):
    pass


@dataclass(frozen=True)
class MacHIDDevice:
    vendor_id: int | None
    product_id: int | None
    usage_page: int | None
    usage: int | None
    name: str | None
    transport: str | None
    location_id: int | None
    registry_id: int | None
    input_report_bytes: int | None
    output_report_bytes: int | None
    feature_report_bytes: int | None

    @property
    def path(self) -> str:
        registry = f"{self.registry_id:x}" if self.registry_id is not None else "unknown"
        return f"ioreg:{registry}"


def _load_framework(name: str) -> ctypes.CDLL:
    path = ctypes.util.find_library(name)
    if path is None:
        raise MacHIDError(f"{name} framework was not found")
    return ctypes.CDLL(path)


_cf = _load_framework("CoreFoundation")
_iokit = _load_framework("IOKit")

_cf.CFStringCreateWithCString.argtypes = [CFTypeRef, ctypes.c_char_p, ctypes.c_uint32]
_cf.CFStringCreateWithCString.restype = CFTypeRef
_cf.CFNumberCreate.argtypes = [CFTypeRef, ctypes.c_int32, ctypes.c_void_p]
_cf.CFNumberCreate.restype = CFTypeRef
_cf.CFNumberGetValue.argtypes = [CFTypeRef, ctypes.c_int32, ctypes.c_void_p]
_cf.CFNumberGetValue.restype = ctypes.c_bool
_cf.CFStringGetCString.argtypes = [CFTypeRef, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
_cf.CFStringGetCString.restype = ctypes.c_bool
_cf.CFDictionaryCreateMutable.argtypes = [
    CFTypeRef,
    ctypes.c_long,
    ctypes.c_void_p,
    ctypes.c_void_p,
]
_cf.CFDictionaryCreateMutable.restype = CFTypeRef
_cf.CFDictionarySetValue.argtypes = [CFTypeRef, CFTypeRef, CFTypeRef]
_cf.CFDictionarySetValue.restype = None
_cf.CFSetGetCount.argtypes = [CFTypeRef]
_cf.CFSetGetCount.restype = ctypes.c_long
_cf.CFSetGetValues.argtypes = [CFTypeRef, ctypes.POINTER(CFTypeRef)]
_cf.CFSetGetValues.restype = None
_cf.CFRelease.argtypes = [CFTypeRef]
_cf.CFRelease.restype = None
_cf.CFRetain.argtypes = [CFTypeRef]
_cf.CFRetain.restype = CFTypeRef
_cf.CFRunLoopRunInMode.argtypes = [CFTypeRef, ctypes.c_double, ctypes.c_bool]
_cf.CFRunLoopRunInMode.restype = ctypes.c_int32
_cf.CFRunLoopGetCurrent.argtypes = []
_cf.CFRunLoopGetCurrent.restype = CFTypeRef

_iokit.IOHIDManagerCreate.argtypes = [CFTypeRef, IOOptionBits]
_iokit.IOHIDManagerCreate.restype = IOHIDManagerRef
_iokit.IOHIDManagerSetDeviceMatching.argtypes = [IOHIDManagerRef, CFTypeRef]
_iokit.IOHIDManagerSetDeviceMatching.restype = None
_iokit.IOHIDManagerOpen.argtypes = [IOHIDManagerRef, IOOptionBits]
_iokit.IOHIDManagerOpen.restype = IOReturn
_iokit.IOHIDManagerClose.argtypes = [IOHIDManagerRef, IOOptionBits]
_iokit.IOHIDManagerClose.restype = IOReturn
_iokit.IOHIDManagerCopyDevices.argtypes = [IOHIDManagerRef]
_iokit.IOHIDManagerCopyDevices.restype = CFTypeRef
_iokit.IOHIDDeviceOpen.argtypes = [IOHIDDeviceRef, IOOptionBits]
_iokit.IOHIDDeviceOpen.restype = IOReturn
_iokit.IOHIDDeviceClose.argtypes = [IOHIDDeviceRef, IOOptionBits]
_iokit.IOHIDDeviceClose.restype = IOReturn
_iokit.IOHIDDeviceGetProperty.argtypes = [IOHIDDeviceRef, CFTypeRef]
_iokit.IOHIDDeviceGetProperty.restype = CFTypeRef
_iokit.IOHIDDeviceGetService.argtypes = [IOHIDDeviceRef]
_iokit.IOHIDDeviceGetService.restype = ctypes.c_uint32
_iokit.IOHIDDeviceSetReport.argtypes = [
    IOHIDDeviceRef,
    ctypes.c_int32,
    ctypes.c_long,
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.c_long,
]
_iokit.IOHIDDeviceSetReport.restype = IOReturn
_iokit.IOHIDDeviceGetReport.argtypes = [
    IOHIDDeviceRef,
    ctypes.c_int32,
    ctypes.c_long,
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.POINTER(ctypes.c_long),
]
_iokit.IOHIDDeviceGetReport.restype = IOReturn
_iokit.IOHIDDeviceRegisterInputReportCallback.argtypes = [
    IOHIDDeviceRef,
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.c_long,
    ctypes.c_void_p,
    ctypes.c_void_p,
]
_iokit.IOHIDDeviceRegisterInputReportCallback.restype = None
_iokit.IOHIDDeviceScheduleWithRunLoop.argtypes = [IOHIDDeviceRef, CFTypeRef, CFTypeRef]
_iokit.IOHIDDeviceScheduleWithRunLoop.restype = None
_iokit.IOHIDDeviceUnscheduleFromRunLoop.argtypes = [IOHIDDeviceRef, CFTypeRef, CFTypeRef]
_iokit.IOHIDDeviceUnscheduleFromRunLoop.restype = None
_iokit.IORegistryEntryGetRegistryEntryID.argtypes = [
    ctypes.c_uint32,
    ctypes.POINTER(ctypes.c_uint64),
]
_iokit.IORegistryEntryGetRegistryEntryID.restype = IOReturn

InputCallback = ctypes.CFUNCTYPE(
    None,
    ctypes.c_void_p,
    IOReturn,
    ctypes.c_void_p,
    ctypes.c_int32,
    ctypes.c_uint32,
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.c_long,
)

_KEYS: dict[str, CFTypeRef] = {}


def _cfstr(value: str) -> CFTypeRef:
    cached = _KEYS.get(value)
    if cached is not None:
        return cached
    ref = _cf.CFStringCreateWithCString(
        None,
        value.encode("utf-8"),
        K_CF_STRING_ENCODING_UTF8,
    )
    if not ref:
        raise MacHIDError(f"could not create CFString for {value!r}")
    _KEYS[value] = ref
    return ref


RUN_LOOP_DEFAULT_MODE = ctypes.c_void_p.in_dll(_cf, "kCFRunLoopDefaultMode")


def _cfnumber(value: int) -> CFTypeRef:
    raw = ctypes.c_int32(value)
    ref = _cf.CFNumberCreate(None, K_CF_NUMBER_SINT32_TYPE, ctypes.byref(raw))
    if not ref:
        raise MacHIDError(f"could not create CFNumber for {value}")
    return ref


def _matching_dict(
    vendor_id: int | None = None,
    product_id: int | None = None,
    usage_page: int | None = None,
    usage: int | None = None,
) -> CFTypeRef:
    dictionary = _cf.CFDictionaryCreateMutable(None, 0, None, None)
    if not dictionary:
        raise MacHIDError("could not create HID matching dictionary")

    for key, value in (
        ("VendorID", vendor_id),
        ("ProductID", product_id),
        ("PrimaryUsagePage", usage_page),
        ("PrimaryUsage", usage),
    ):
        if value is None:
            continue
        number = _cfnumber(value)
        _cf.CFDictionarySetValue(dictionary, _cfstr(key), number)
        _cf.CFRelease(number)
    return dictionary


def _number_property(device: IOHIDDeviceRef, key: str) -> int | None:
    ref = _iokit.IOHIDDeviceGetProperty(device, _cfstr(key))
    if not ref:
        return None
    value = ctypes.c_int32()
    if not _cf.CFNumberGetValue(ref, K_CF_NUMBER_SINT32_TYPE, ctypes.byref(value)):
        return None
    return int(value.value)


def _string_property(device: IOHIDDeviceRef, key: str) -> str | None:
    ref = _iokit.IOHIDDeviceGetProperty(device, _cfstr(key))
    if not ref:
        return None
    buffer = ctypes.create_string_buffer(512)
    if not _cf.CFStringGetCString(ref, buffer, len(buffer), K_CF_STRING_ENCODING_UTF8):
        return None
    return buffer.value.decode("utf-8", errors="replace")


def _registry_id(device: IOHIDDeviceRef) -> int | None:
    service = _iokit.IOHIDDeviceGetService(device)
    if not service:
        return None
    value = ctypes.c_uint64()
    status = _iokit.IORegistryEntryGetRegistryEntryID(service, ctypes.byref(value))
    if status != 0:
        return None
    return int(value.value)


def _device_info(device: IOHIDDeviceRef) -> MacHIDDevice:
    return MacHIDDevice(
        vendor_id=_number_property(device, "VendorID"),
        product_id=_number_property(device, "ProductID"),
        usage_page=_number_property(device, "PrimaryUsagePage"),
        usage=_number_property(device, "PrimaryUsage"),
        name=_string_property(device, "Product"),
        transport=_string_property(device, "Transport"),
        location_id=_number_property(device, "LocationID"),
        registry_id=_registry_id(device),
        input_report_bytes=_number_property(device, "MaxInputReportSize"),
        output_report_bytes=_number_property(device, "MaxOutputReportSize"),
        feature_report_bytes=_number_property(device, "MaxFeatureReportSize"),
    )


def enumerate_hid_macos(
    vendor_id: int | None = None,
    product_id: int | None = None,
    usage_page: int | None = None,
    usage: int | None = None,
) -> list[MacHIDDevice]:
    manager = _iokit.IOHIDManagerCreate(None, K_IOHID_OPTIONS_TYPE_NONE)
    if not manager:
        raise MacHIDError("could not create IOHIDManager")

    matching = _matching_dict(vendor_id, product_id, usage_page, usage)
    try:
        _iokit.IOHIDManagerSetDeviceMatching(manager, matching)
        device_set = _iokit.IOHIDManagerCopyDevices(manager)
        if not device_set:
            return []
        try:
            count = _cf.CFSetGetCount(device_set)
            values = (CFTypeRef * count)()
            _cf.CFSetGetValues(device_set, values)
            return [_device_info(IOHIDDeviceRef(value)) for value in values]
        finally:
            _cf.CFRelease(device_set)
    finally:
        _cf.CFRelease(matching)
        _cf.CFRelease(manager)


def find_matching_device(
    vendor_id: int,
    product_id: int,
    usage_page: int | None = None,
    usage: int | None = None,
) -> MacHIDDevice:
    devices = enumerate_hid_macos(vendor_id, product_id, usage_page, usage)
    for device in devices:
        if device.vendor_id != vendor_id or device.product_id != product_id:
            continue
        if usage_page is not None and device.usage_page != usage_page:
            continue
        if usage is not None and device.usage != usage:
            continue
        return device
    raise FileNotFoundError(
        "no matching macOS HID device found"
        f" (vid=0x{vendor_id:04x}, pid=0x{product_id:04x},"
        f" usage_page={usage_page!r}, usage={usage!r})"
    )


class MacHIDTransport:
    def __init__(
        self,
        vendor_id: int,
        product_id: int,
        usage_page: int | None,
        usage: int | None,
        timeout_seconds: float = 1.0,
        input_report_bytes: int = 32,
        seize: bool = False,
    ) -> None:
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.usage_page = usage_page
        self.usage = usage
        self.timeout_seconds = timeout_seconds
        self.input_report_bytes = input_report_bytes
        self.seize = seize
        self.report_size: int | None = input_report_bytes
        self.device_info: MacHIDDevice | None = None

        self._manager: IOHIDManagerRef | None = None
        self._matching: CFTypeRef | None = None
        self._device: IOHIDDeviceRef | None = None
        self._run_loop: CFTypeRef | None = None
        self._input_buffer: ctypes.Array[ctypes.c_uint8] | None = None
        self._callback: InputCallback | None = None
        self._reports: queue.Queue[bytes] = queue.Queue()

    def __enter__(self) -> "MacHIDTransport":
        manager = _iokit.IOHIDManagerCreate(None, K_IOHID_OPTIONS_TYPE_NONE)
        if not manager:
            raise MacHIDError("could not create IOHIDManager")
        self._manager = manager
        self._matching = _matching_dict(
            self.vendor_id,
            self.product_id,
            self.usage_page,
            self.usage,
        )
        _iokit.IOHIDManagerSetDeviceMatching(manager, self._matching)
        device_set = _iokit.IOHIDManagerCopyDevices(manager)
        if not device_set:
            self.__exit__(None, None, None)
            raise FileNotFoundError("matching macOS HID device is not present")
        try:
            count = _cf.CFSetGetCount(device_set)
            if count < 1:
                raise FileNotFoundError("matching macOS HID device is not present")
            values = (CFTypeRef * count)()
            _cf.CFSetGetValues(device_set, values)
            self._device = IOHIDDeviceRef(_cf.CFRetain(values[0]))
        finally:
            _cf.CFRelease(device_set)

        self.device_info = _device_info(self._device)
        open_options = K_IOHID_OPTIONS_TYPE_SEIZE_DEVICE if self.seize else K_IOHID_OPTIONS_TYPE_NONE
        status = _iokit.IOHIDDeviceOpen(self._device, open_options)
        if status != 0:
            self.__exit__(None, None, None)
            raise MacHIDError(f"IOHIDDeviceOpen failed: 0x{status & 0xffffffff:08x}")

        self.input_report_bytes = (
            self.device_info.input_report_bytes
            or self.device_info.output_report_bytes
            or self.input_report_bytes
        )
        self.report_size = self.input_report_bytes
        self._input_buffer = (ctypes.c_uint8 * (self.input_report_bytes + 1))()
        self._callback = InputCallback(self._handle_input_report)
        _iokit.IOHIDDeviceRegisterInputReportCallback(
            self._device,
            self._input_buffer,
            self.input_report_bytes + 1,
            self._callback,
            None,
        )
        self._run_loop = _cf.CFRunLoopGetCurrent()
        _iokit.IOHIDDeviceScheduleWithRunLoop(
            self._device,
            self._run_loop,
            RUN_LOOP_DEFAULT_MODE,
        )
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._device and self._run_loop:
            _iokit.IOHIDDeviceUnscheduleFromRunLoop(
                self._device,
                self._run_loop,
                RUN_LOOP_DEFAULT_MODE,
            )
        if self._device:
            open_options = K_IOHID_OPTIONS_TYPE_SEIZE_DEVICE if self.seize else K_IOHID_OPTIONS_TYPE_NONE
            _iokit.IOHIDDeviceClose(self._device, open_options)
            _cf.CFRelease(self._device)
            self._device = None
        if self._manager:
            _iokit.IOHIDManagerClose(self._manager, K_IOHID_OPTIONS_TYPE_NONE)
            _cf.CFRelease(self._manager)
            self._manager = None
        if self._matching:
            _cf.CFRelease(self._matching)
            self._matching = None
        self._run_loop = None
        self._input_buffer = None
        self._callback = None

    def _handle_input_report(
        self,
        context,
        result,
        sender,
        report_type,
        report_id,
        report,
        report_length,
    ) -> None:
        if result != 0 or not report:
            return
        self._reports.put(bytes(report[i] for i in range(report_length)))

    def write(self, payload: bytes) -> int:
        return self.set_report(
            report_type=K_IOHID_REPORT_TYPE_OUTPUT,
            report_id=0,
            payload=payload,
            prefix_report_id=False,
        )

    def set_report(
        self,
        report_type: int,
        report_id: int,
        payload: bytes,
        prefix_report_id: bool = False,
    ) -> int:
        if self._device is None:
            raise RuntimeError("device is not open")
        report = bytes([report_id]) + payload if prefix_report_id else payload
        buffer = (ctypes.c_uint8 * len(report)).from_buffer_copy(report)
        status = _iokit.IOHIDDeviceSetReport(
            self._device,
            report_type,
            report_id,
            buffer,
            len(report),
        )
        if status != 0:
            raise MacHIDError(f"IOHIDDeviceSetReport failed: 0x{status & 0xffffffff:08x}")
        return len(payload)

    def get_report(self, report_type: int, report_id: int, length: int) -> bytes:
        if self._device is None:
            raise RuntimeError("device is not open")
        buffer = (ctypes.c_uint8 * length)()
        buffer[0] = report_id
        report_length = ctypes.c_long(length)
        status = _iokit.IOHIDDeviceGetReport(
            self._device,
            report_type,
            report_id,
            buffer,
            ctypes.byref(report_length),
        )
        if status != 0:
            raise MacHIDError(f"IOHIDDeviceGetReport failed: 0x{status & 0xffffffff:08x}")
        return bytes(buffer[i] for i in range(report_length.value))

    def read_report(self, max_length: int = 64) -> bytes:
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                report = self._reports.get_nowait()
                return report[:max_length]
            except queue.Empty:
                pass

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("timed out waiting for a macOS HID input report")
            _cf.CFRunLoopRunInMode(RUN_LOOP_DEFAULT_MODE, min(0.05, remaining), False)

    def drain_pending_reports(self, max_reads: int = 32) -> list[bytes]:
        drained: list[bytes] = []
        for _ in range(max_reads):
            _cf.CFRunLoopRunInMode(RUN_LOOP_DEFAULT_MODE, 0.001, False)
            try:
                drained.append(self._reports.get_nowait())
            except queue.Empty:
                break
        return drained
