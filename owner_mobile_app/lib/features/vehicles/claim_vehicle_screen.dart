import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';
import 'vehicles_provider.dart';

class ClaimVehicleScreen extends StatefulWidget {
  const ClaimVehicleScreen({super.key});

  @override
  State<ClaimVehicleScreen> createState() => _ClaimVehicleScreenState();
}

class _ClaimVehicleScreenState extends State<ClaimVehicleScreen> {
  final _formKey = GlobalKey<FormState>();
  final _vinCtrl = TextEditingController();
  bool _loading = false;

  @override
  void dispose() {
    _vinCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _loading = true);
    final error = await context
        .read<VehiclesProvider>()
        .claimVehicle(_vinCtrl.text.trim().toUpperCase());
    if (!mounted) return;
    setState(() => _loading = false);
    if (error == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Vehicle claimed successfully'),
            backgroundColor: Colors.green),
      );
      context.pop();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error), backgroundColor: Colors.red),
      );
    }
  }

  Future<void> _scanQr() async {
    final result = await Navigator.push<String>(
      context,
      MaterialPageRoute(builder: (_) => const _QrScannerScreen()),
    );
    if (result != null && mounted) {
      _vinCtrl.text = result.toUpperCase();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Claim Vehicle')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Icon(Icons.directions_car, size: 64, color: Colors.grey),
              const SizedBox(height: 16),
              Text(
                'Enter your vehicle\'s VIN to claim ownership',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey[600]),
              ),
              const SizedBox(height: 32),
              TextFormField(
                controller: _vinCtrl,
                textCapitalization: TextCapitalization.characters,
                decoration: InputDecoration(
                  labelText: 'Vehicle Identification Number (VIN)',
                  hintText: 'e.g. 1HGBH41JXMN109186',
                  prefixIcon: const Icon(Icons.tag),
                  suffixIcon: IconButton(
                    icon: const Icon(Icons.qr_code_scanner),
                    tooltip: 'Scan VIN barcode',
                    onPressed: _scanQr,
                  ),
                ),
                validator: (v) {
                  if (v == null || v.trim().isEmpty) return 'VIN required';
                  if (v.trim().length != 17) return 'VIN must be 17 characters';
                  return null;
                },
              ),
              const SizedBox(height: 8),
              TextButton.icon(
                onPressed: _scanQr,
                icon: const Icon(Icons.qr_code_scanner),
                label: const Text('Scan VIN Barcode / QR Code'),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _loading ? null : _submit,
                child: _loading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                            color: Colors.white, strokeWidth: 2))
                    : const Text('Claim Vehicle'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _QrScannerScreen extends StatefulWidget {
  const _QrScannerScreen();

  @override
  State<_QrScannerScreen> createState() => _QrScannerScreenState();
}

class _QrScannerScreenState extends State<_QrScannerScreen> {
  late final MobileScannerController _controller;
  bool _scanned = false;

  @override
  void initState() {
    super.initState();
    _controller = MobileScannerController(
      facing: CameraFacing.back,
      detectionSpeed: DetectionSpeed.normal,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _onDetect(BarcodeCapture capture) {
    if (_scanned) return;
    final barcode = capture.barcodes.firstOrNull;
    final raw = barcode?.rawValue;
    if (raw == null || raw.isEmpty) return;
    _scanned = true;
    _controller.stop();
    final vin = _extractVin(raw);
    Navigator.pop(context, vin ?? raw);
  }

  static String? _extractVin(String raw) {
    final vinRe = RegExp(r'^[A-HJ-NPR-Z0-9]{17}$', caseSensitive: false);
    if (vinRe.hasMatch(raw.trim())) return raw.trim().toUpperCase();
    final urlMatch = RegExp(r'[/=]([A-HJ-NPR-Z0-9]{17})(?:[/?#]|$)', caseSensitive: false)
        .firstMatch(raw);
    if (urlMatch != null) return urlMatch.group(1)!.toUpperCase();
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scan VIN')),
      body: Stack(
        children: [
          MobileScanner(
            controller: _controller,
            onDetect: _onDetect,
            errorBuilder: (context, error, child) {
              final isPermission =
                  error.errorCode == MobileScannerErrorCode.permissionDenied;
              return ColoredBox(
                color: Colors.black,
                child: Center(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 32),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          isPermission
                              ? Icons.no_photography_outlined
                              : Icons.camera_alt_outlined,
                          color: Colors.white54,
                          size: 64,
                        ),
                        const SizedBox(height: 16),
                        Text(
                          isPermission
                              ? 'Camera permission required.\n\nTap Retry, then allow camera access when prompted.'
                              : 'Camera could not start.\nTap Retry to try again.',
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                              color: Colors.white70, fontSize: 14, height: 1.5),
                        ),
                        const SizedBox(height: 24),
                        ElevatedButton.icon(
                          onPressed: () => _controller.start(),
                          icon: const Icon(Icons.refresh),
                          label: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
          Center(
            child: Container(
              width: 260,
              height: 100,
              decoration: BoxDecoration(
                border: Border.all(color: Colors.white, width: 2),
                borderRadius: BorderRadius.circular(8),
              ),
            ),
          ),
          const Positioned(
            bottom: 40,
            left: 0,
            right: 0,
            child: Text(
              'Align barcode or QR code within the frame',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white, fontSize: 14),
            ),
          ),
        ],
      ),
    );
  }
}
