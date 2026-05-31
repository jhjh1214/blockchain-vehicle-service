import { Component, OnInit, OnDestroy, AfterViewInit, ElementRef, ViewChild, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import * as L from 'leaflet';
import { ScManagementService, ServiceCenter } from '../../../core/services/sc-management.service';
import { MY_CITIES, getCityCoords } from '../../../shared/constants/my-cities';

// Fix leaflet default marker icons (broken in webpack builds)
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl:       'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl:     'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

@Component({
  selector: 'app-service-centers',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './service-centers.html',
  styleUrls: ['./service-centers.css'],
})
export class ServiceCentersComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('mapEl') mapEl!: ElementRef<HTMLDivElement>;

  serviceCenters: ServiceCenter[] = [];
  loading = true;
  error = '';
  fundAllLoading = false;
  fundAllAmount = 0.1;
  fundAllMsg = '';

  // Filters
  searchText = '';
  filterStatus = '';
  filterState = '';

  states = [...new Set(MY_CITIES.map(c => c.state))].sort();

  private map!: L.Map;
  private markers: L.Marker[] = [];

  constructor(
    private scService: ScManagementService,
    private router: Router,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.load();
  }

  ngAfterViewInit(): void {
    setTimeout(() => this.initMap(), 0);
  }

  ngOnDestroy(): void {
    this.map?.remove();
  }

  private initMap(): void {
    this.map = L.map(this.mapEl.nativeElement, {
      center: [4.2105, 108.9758],  // Malaysia center
      zoom: 6,
    });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      attribution: '© <a href="https://www.openstreetmap.org/">OpenStreetMap</a>',
    }).addTo(this.map);
  }

  load(): void {
    this.loading = true;
    this.error = '';
    this.scService.getServiceCenters({
      search: this.searchText,
      status: this.filterStatus,
      state:  this.filterState,
      limit:  200,
    }).subscribe({
      next: res => {
        this.serviceCenters = res.items;
        this.loading = false;
        this.cdr.detectChanges();
        this.updateMapMarkers();
      },
      error: () => {
        this.error = 'Failed to load service centers';
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }

  private updateMapMarkers(): void {
    if (!this.map) return;
    this.map.invalidateSize();
    this.markers.forEach(m => m.remove());
    this.markers = [];

    this.serviceCenters.forEach(sc => {
      const coords = getCityCoords(sc.city);
      if (!coords) return;

      const color = sc.status === 'active' ? '#22c55e'
                  : sc.status === 'pending' ? '#f59e0b'
                  : '#ef4444';

      const icon = L.divIcon({
        className: '',
        html: `<div style="width:14px;height:14px;background:${color};border:2px solid white;border-radius:50%;box-shadow:0 1px 4px rgba(0,0,0,.4)"></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      });

      const marker = L.marker([coords.lat, coords.lng], { icon })
        .addTo(this.map)
        .bindPopup(`
          <strong>${sc.name || sc.email}</strong><br>
          ${sc.city}, ${sc.state}<br>
          <span style="color:${color};font-weight:600;text-transform:capitalize">${sc.status}</span>
          <br><a href="/manufacturer/service-centers/${sc.id}" style="color:#3b82f6">View details →</a>
        `);

      this.markers.push(marker);
    });
  }

  applyFilters(): void {
    this.load();
  }

  clearFilters(): void {
    this.searchText = '';
    this.filterStatus = '';
    this.filterState = '';
    this.load();
  }

  openDetail(id: number): void {
    this.router.navigate(['/manufacturer/service-centers', id]);
  }

  fundAll(): void {
    if (this.fundAllLoading) return;
    this.fundAllLoading = true;
    this.fundAllMsg = '';
    this.scService.fundAll(this.fundAllAmount).subscribe({
      next: r => {
        this.fundAllMsg = r.message;
        this.fundAllLoading = false;
        this.cdr.detectChanges();
        this.load();
      },
      error: e => {
        this.fundAllMsg = e.error?.error || 'Funding failed';
        this.fundAllLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  statusLabel(s: string): string {
    return { active: 'Active', pending: 'Pending', suspended: 'Suspended' }[s] ?? s;
  }

  get activeSCs(): number { return this.serviceCenters.filter(s => s.status === 'active').length; }
  get pendingSCs(): number { return this.serviceCenters.filter(s => s.status === 'pending').length; }
  get suspendedSCs(): number { return this.serviceCenters.filter(s => s.status === 'suspended').length; }
}
