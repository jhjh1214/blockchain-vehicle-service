import 'dart:io';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import 'warranties_provider.dart';

class SubmitClaimScreen extends StatefulWidget {
  final String vin;
  const SubmitClaimScreen({super.key, required this.vin});

  @override
  State<SubmitClaimScreen> createState() => _SubmitClaimScreenState();
}

class _SubmitClaimScreenState extends State<SubmitClaimScreen> {
  final _formKey = GlobalKey<FormState>();
  final _descriptionCtrl = TextEditingController();
  final _picker = ImagePicker();
  List<XFile> _photos = [];
  bool _loading = false;

  @override
  void dispose() {
    _descriptionCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickPhotos() async {
    final remaining = 3 - _photos.length;
    if (remaining <= 0) return;
    final picked = await _picker.pickMultiImage(imageQuality: 70, limit: remaining);
    if (picked.isNotEmpty) setState(() => _photos.addAll(picked));
  }

  void _removePhoto(int index) => setState(() => _photos.removeAt(index));

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _loading = true);
    final error = await context.read<WarrantiesProvider>().submitClaim(
          widget.vin,
          _descriptionCtrl.text.trim(),
          photos: _photos,
        );
    if (!mounted) return;
    setState(() => _loading = false);
    if (error == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Warranty claim submitted'), backgroundColor: Colors.green),
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
      appBar: AppBar(title: const Text('Submit Warranty Claim')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Row(children: [
                    const Icon(Icons.directions_car, color: Colors.grey),
                    const SizedBox(width: 12),
                    Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      const Text('Vehicle VIN', style: TextStyle(color: Colors.grey, fontSize: 12)),
                      Text(widget.vin,
                          style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w600)),
                    ]),
                  ]),
                ),
              ),
              const SizedBox(height: 20),
              TextFormField(
                controller: _descriptionCtrl,
                maxLines: 5,
                decoration: const InputDecoration(
                  labelText: 'Issue Description *',
                  hintText: 'Describe the issue in detail. Include when it started, symptoms, and relevant information.',
                  alignLabelWithHint: true,
                ),
                validator: (v) {
                  if (v == null || v.trim().isEmpty) return 'Description required';
                  if (v.trim().length < 20) return 'Please provide a more detailed description (min 20 chars)';
                  return null;
                },
              ),
              const SizedBox(height: 20),
              Row(children: [
                const Text('Supporting Photos',
                    style: TextStyle(fontWeight: FontWeight.w500, fontSize: 14)),
                const SizedBox(width: 6),
                Text('(${_photos.length}/3 — optional)',
                    style: const TextStyle(color: Colors.grey, fontSize: 12)),
              ]),
              const SizedBox(height: 8),
              if (_photos.isNotEmpty)
                SizedBox(
                  height: 90,
                  child: ListView.separated(
                    scrollDirection: Axis.horizontal,
                    itemCount: _photos.length,
                    separatorBuilder: (_, __) => const SizedBox(width: 8),
                    itemBuilder: (_, i) => Stack(children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: Image.file(
                          File(_photos[i].path),
                          width: 80, height: 80, fit: BoxFit.cover,
                        ),
                      ),
                      Positioned(
                        top: 2, right: 2,
                        child: GestureDetector(
                          onTap: () => _removePhoto(i),
                          child: Container(
                            width: 20, height: 20,
                            decoration: const BoxDecoration(
                                color: Colors.black54, shape: BoxShape.circle),
                            child: const Icon(Icons.close, size: 14, color: Colors.white),
                          ),
                        ),
                      ),
                    ]),
                  ),
                ),
              if (_photos.length < 3)
                OutlinedButton.icon(
                  onPressed: _pickPhotos,
                  icon: const Icon(Icons.add_photo_alternate_outlined, size: 18),
                  label: Text(_photos.isEmpty
                      ? 'Add Photos'
                      : 'Add More (${3 - _photos.length} remaining)'),
                ),
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: _loading ? null : _submit,
                child: _loading
                    ? const SizedBox(
                        height: 20, width: 20,
                        child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                    : const Text('Submit Claim'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
