import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
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
                decoration: const InputDecoration(
                  labelText: 'Vehicle Identification Number (VIN)',
                  hintText: 'e.g. 1HGBH41JXMN109186',
                  prefixIcon: Icon(Icons.tag),
                ),
                validator: (v) {
                  if (v == null || v.trim().isEmpty) return 'VIN required';
                  if (v.trim().length != 17) return 'VIN must be 17 characters';
                  return null;
                },
              ),
              const SizedBox(height: 24),
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
