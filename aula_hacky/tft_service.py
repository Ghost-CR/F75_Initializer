from __future__ import annotations

import time

from .hid_macos import K_IOHID_REPORT_TYPE_FEATURE, MacHIDTransport, find_matching_device
from .macos_cli import _format_device_line
from .tft_protocol import (
    SCREEN_CHUNK_BYTES,
    SCREEN_CONTROL_USAGE,
    SCREEN_CONTROL_USAGE_PAGE,
    SCREEN_PIPE_USAGE,
    SCREEN_PIPE_USAGE_PAGE,
    WIRED_PID,
    WIRED_VID,
    ScreenStream,
    build_control_command,
    build_metadata_command,
    iter_chunks,
)


class TFTTransactionError(RuntimeError):
    """Raised when a screen upload cannot be completed atomically.

    The keyboard firmware may be left waiting for remaining chunks. The
    safest recovery is to disconnect and reconnect the USB-C cable.
    """

    pass


class TFTService:
    """Atomic TFT screen upload service for AULA F75 Max over USB-C.

    This class guarantees that a screen upload is either fully delivered or
    aborted without sending the final ``exit`` command on an incomplete
    stream. Sending ``exit`` prematurely (e.g. after only a subset of chunks)
    leaves the keyboard firmware in a "loading" state that blocks all other
    features including RGB and RTC.
    """

    def __init__(
        self,
        timeout_seconds: float = 1.0,
        debug: bool = False,
        chunk_delay_seconds: float = 0.04,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.debug = debug
        self.chunk_delay_seconds = chunk_delay_seconds

    def _open_transports(self) -> tuple[MacHIDTransport, MacHIDTransport]:
        control_info = find_matching_device(
            WIRED_VID,
            WIRED_PID,
            SCREEN_CONTROL_USAGE_PAGE,
            SCREEN_CONTROL_USAGE,
        )
        pipe_info = find_matching_device(
            WIRED_VID,
            WIRED_PID,
            SCREEN_PIPE_USAGE_PAGE,
            SCREEN_PIPE_USAGE,
        )
        if self.debug:
            print(f"control-device: {_format_device_line(control_info)}")
            print(f"pipe-device: {_format_device_line(pipe_info)}")

        control = MacHIDTransport(
            WIRED_VID,
            WIRED_PID,
            SCREEN_CONTROL_USAGE_PAGE,
            SCREEN_CONTROL_USAGE,
            timeout_seconds=self.timeout_seconds,
            input_report_bytes=64,
        )
        pipe = MacHIDTransport(
            WIRED_VID,
            WIRED_PID,
            SCREEN_PIPE_USAGE_PAGE,
            SCREEN_PIPE_USAGE,
            timeout_seconds=self.timeout_seconds,
            input_report_bytes=64,
        )
        return control, pipe

    def _send_control(self, transport: MacHIDTransport, payload: bytes, label: str) -> None:
        written = transport.set_report(
            K_IOHID_REPORT_TYPE_FEATURE,
            report_id=0,
            payload=payload,
            prefix_report_id=False,
        )
        if written != 64:
            raise TFTTransactionError(
                f"{label}: short control write, wrote {written} bytes"
            )
        if self.debug:
            print(f"{label}: feature={payload.hex()}")

    def _send_begin(self, control: MacHIDTransport) -> None:
        self._send_control(control, build_control_command(bytes([0x04, 0x18])), "screen-begin")
        time.sleep(0.2)

    def _send_metadata(self, control: MacHIDTransport, chunk_count: int, slot: int) -> None:
        self._send_control(
            control,
            build_metadata_command(chunk_count, slot),
            "screen-metadata",
        )
        time.sleep(0.05)

    def _send_chunks(self, pipe: MacHIDTransport, stream: ScreenStream) -> None:
        for index, chunk in enumerate(iter_chunks(stream.data), start=1):
            written = pipe.write(chunk)
            if written != SCREEN_CHUNK_BYTES:
                raise TFTTransactionError(
                    f"screen-chunk-{index}/{stream.chunk_count}: short write, "
                    f"wrote {written} bytes"
                )
            if self.debug:
                print(f"screen-chunk: {index}/{stream.chunk_count}")
            time.sleep(self.chunk_delay_seconds)

    def _send_exit(self, control: MacHIDTransport) -> None:
        time.sleep(0.1)
        self._send_control(control, build_control_command(bytes([0x04, 0x02])), "screen-exit")

    def upload(self, stream: ScreenStream, slot: int = 1) -> None:
        """Upload a screen stream atomically.

        Raises:
            TFTTransactionError: if any step fails before the stream is fully
                sent. Do **not** send the ``exit`` command manually; the safest
                recovery is to disconnect and reconnect the USB-C cable.
        """
        control: MacHIDTransport | None = None
        pipe: MacHIDTransport | None = None

        try:
            control, pipe = self._open_transports()
            control.__enter__()
            pipe.__enter__()

            # Drain stale reports before starting a new transaction.
            pipe.drain_pending_reports()

            self._send_begin(control)
            self._send_metadata(control, stream.chunk_count, slot)
            self._send_chunks(pipe, stream)
            self._send_exit(control)
        except Exception as exc:
            # Do not send exit on a partial stream; that is what locks the
            # keyboard into a "loading" state.
            if not isinstance(exc, TFTTransactionError):
                raise TFTTransactionError(
                    f"Screen upload failed mid-transaction: {exc}\n"
                    "Recovery: disconnect and reconnect the USB-C cable."
                ) from exc
            raise
        finally:
            if pipe is not None:
                pipe.__exit__(None, None, None)
            if control is not None:
                control.__exit__(None, None, None)
