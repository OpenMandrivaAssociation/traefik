%undefine _debugsource_packages

# Module shared objects live here (see MODULES_REPORT.md).
%global traefik_moddir %{_prefix}/lib/traefik/modules
%global traefik_webuidir %{_datadir}/traefik/webui

Name:		traefik
Version:	3.7.12
Release:	1
Source0:	https://github.com/traefik/traefik/releases/download/v%{version}/traefik-v%{version}.src.tar.gz
Source1:	vendor.tar.xz
Source2:	traefik.yml
Source3:	traefik.logrotate
Summary:	The Traefik application proxy (full installation)
URL:		https://doc.traefik.io/traefik
License:	MIT
Group:		Servers
BuildRequires:	golang

# Full install pulls in the core binary and every module package.
Requires:	traefik-core = %{EVRD}
Requires:	traefik-mod-docker = %{EVRD}
Requires:	traefik-mod-kubernetes = %{EVRD}
Requires:	traefik-mod-consul = %{EVRD}
Requires:	traefik-mod-nomad = %{EVRD}
Requires:	traefik-mod-etcd = %{EVRD}
Requires:	traefik-mod-redis = %{EVRD}
Requires:	traefik-mod-zookeeper = %{EVRD}
Requires:	traefik-mod-ecs = %{EVRD}
Requires:	traefik-mod-webui = %{EVRD}

%patchlist
traefik-3.6.8-fix-bogus-deps.patch
traefik-modular.patch

%description
Traefik (pronounced traffic) is a modern HTTP reverse proxy and load balancer
that makes deploying microservices easy.

This is a meta-package that installs the core binary together with all
optional provider modules (Docker, Kubernetes, Consul, Nomad, etcd, Redis,
ZooKeeper, ECS) and the dashboard WebUI. For a minimal install, depend on
traefik-core and only the module packages you need.

%package core
Summary:	Traefik core reverse proxy binary and service
Group:		Servers
Requires(pre):	shadow-utils
Recommends:	traefik-mod-docker = %{EVRD}
Recommends:	traefik-mod-webui = %{EVRD}

%description core
Core Traefik reverse proxy binary, systemd unit, and configuration.
Includes the routing engine, file/HTTP/REST providers (built in), and the
loadable-module infrastructure. Optional providers are supplied by the
traefik-mod-* packages as shared objects under %{traefik_moddir}.

%package mod-docker
Summary:	Traefik Docker and Swarm provider modules
Group:		Servers
Requires:	traefik-core = %{EVRD}

%description mod-docker
Loadable modules for Docker container discovery and Docker Swarm service
discovery (traefik-docker.so, traefik-swarm.so).

%package mod-kubernetes
Summary:	Traefik Kubernetes provider modules
Group:		Servers
Requires:	traefik-core = %{EVRD}

%description mod-kubernetes
Loadable modules for Kubernetes CRD, Ingress, Gateway API, Ingress-NGINX
compatibility, and Knative providers.

%package mod-consul
Summary:	Traefik Consul provider modules
Group:		Servers
Requires:	traefik-core = %{EVRD}

%description mod-consul
Loadable modules for Consul Catalog and Consul KV providers.

%package mod-nomad
Summary:	Traefik Nomad provider module
Group:		Servers
Requires:	traefik-core = %{EVRD}

%description mod-nomad
Loadable module for HashiCorp Nomad service discovery.

%package mod-etcd
Summary:	Traefik etcd provider module
Group:		Servers
Requires:	traefik-core = %{EVRD}

%description mod-etcd
Loadable module for etcd key-value configuration provider.

%package mod-redis
Summary:	Traefik Redis provider module
Group:		Servers
Requires:	traefik-core = %{EVRD}

%description mod-redis
Loadable module for Redis key-value configuration provider.

%package mod-zookeeper
Summary:	Traefik ZooKeeper provider module
Group:		Servers
Requires:	traefik-core = %{EVRD}

%description mod-zookeeper
Loadable module for ZooKeeper key-value configuration provider.

%package mod-ecs
Summary:	Traefik AWS ECS provider module
Group:		Servers
Requires:	traefik-core = %{EVRD}

%description mod-ecs
Loadable module for AWS ECS service discovery.

%package mod-webui
Summary:	Traefik dashboard WebUI module and assets
Group:		Servers
Requires:	traefik-core = %{EVRD}

%description mod-webui
Dashboard web interface: static assets under %{traefik_webuidir} and the
optional traefik-webui.so module for on-demand loading from disk.

%prep
%autosetup -p1 -c -n %{name}-%{version} -a1

%conf
go generate

%build
# Shared ldflags so the core binary and plugins stay ABI-compatible.
build_date=$(date -u +%%Y-%%m-%%dT%%H:%%M:%%SZ)
LDFLAGS="-X github.com/traefik/traefik/v3/pkg/version.Version=%{version} \
	-X github.com/traefik/traefik/v3/pkg/version.Codename='' \
	-X github.com/traefik/traefik/v3/pkg/version.BuildDate=${build_date}"

export CGO_ENABLED=1

# Core binary (built-ins still register as fallback when a .so is absent).
go build \
	-mod=vendor \
	-ldflags "${LDFLAGS}" \
	-o traefik \
	./cmd/traefik

# Loadable provider / webui modules (Go plugins).
mkdir -p build-modules
# name:plugin-dir pairs (output so name uses traefik-<name>.so)
for spec in \
	docker:docker \
	swarm:swarm \
	kubernetes-crd:kubernetes-crd \
	kubernetes-ingress:kubernetes-ingress \
	kubernetes-gateway:kubernetes-gateway \
	kubernetes-ingress-nginx:kubernetes-ingress-nginx \
	knative:knative \
	consul-catalog:consul-catalog \
	consul:consul \
	nomad:nomad \
	etcd:etcd \
	zookeeper:zookeeper \
	redis:redis \
	ecs:ecs \
	webui:webui
do
	name=${spec%%:*}
	dir=${spec##*:}
	echo "Building module traefik-${name}.so from ./plugins/${dir}"
	go build \
		-buildmode=plugin \
		-mod=vendor \
		-o "build-modules/traefik-${name}.so" \
		"./plugins/${dir}"
done

%install
mkdir -p \
	%{buildroot}%{_bindir} \
	%{buildroot}%{_sysusersdir} \
	%{buildroot}%{_unitdir} \
	%{buildroot}%{_sysconfdir}/traefik \
	%{buildroot}%{_sysconfdir}/traefik/conf.d \
	%{buildroot}%{traefik_moddir} \
	%{buildroot}%{traefik_webuidir} \
	%{buildroot}/srv/traefik \
	%{buildroot}%{_localstatedir}/log/traefik \
	%{buildroot}%{_sysconfdir}/logrotate.d \
	%{buildroot}%{_sysconfdir}/sysconfig

install -m 755 traefik %{buildroot}%{_bindir}/traefik
install -m 644 %{S:2} %{buildroot}%{_sysconfdir}/traefik/traefik.yml
install -m 644 %{S:3} %{buildroot}%{_sysconfdir}/logrotate.d/traefik

# Module shared objects
install -m 755 build-modules/*.so %{buildroot}%{traefik_moddir}/

# Dashboard static assets (used by webui module when not embedding)
cp -a webui/static/. %{buildroot}%{traefik_webuidir}/

# acme storage placeholder
touch %{buildroot}/srv/traefik/acme.json

cat >%{buildroot}%{_sysusersdir}/%{name}.conf <<EOF
u	traefik	-	"HTTP reverse proxy and load balancer"	/srv/traefik	-
m	traefik	traefik
m	traefik	docker
EOF

cat >%{buildroot}%{_unitdir}/%{name}.service <<'EOF'
[Unit]
Description=Traefik
Documentation=https://doc.traefik.io/traefik/
After=network.target network-online.target
Requires=network-online.target
AssertFileIsExecutable=%{_bindir}/traefik
AssertPathExists=%{_sysconfdir}/traefik/traefik.yml

[Service]
Type=notify
EnvironmentFile=-%{_sysconfdir}/sysconfig/traefik
ExecStart=%{_bindir}/traefik --configFile=%{_sysconfdir}/traefik/traefik.yml
ExecReload=kill -HUP $MAINPID ; kill -USR1 $MAINPID
User=traefik
WorkingDirectory=~
Restart=always
WatchdogSec=1s
PrivateTmp=true
ProtectSystem=full
AmbientCapabilities=CAP_NET_BIND_SERVICE
KillMode=mixed

[Install]
WantedBy=multi-user.target
EOF

cat >%{buildroot}%{_sysconfdir}/sysconfig/traefik <<EOF
# PowerDNS API Configuration for Traefik ACME DNS-01 Challenge
#PDNS_API_URL=http://127.0.0.1:8081
# Keep in sync with api-key= in /etc/powerdns/pdns.conf
#PDNS_API_KEY=your_api_key_here

# Optional: Time in seconds to wait for DNS propagation before
# Traefik checks it
PDNS_PROPAGATION_DELAY=30
EOF

# Meta package needs at least one file in some RPM tooling; ship a short README.
mkdir -p %{buildroot}%{_docdir}/traefik
cat >%{buildroot}%{_docdir}/traefik/MODULES.txt <<EOF
Traefik modular installation
============================

Core binary:  traefik-core
Modules dir:  %{traefik_moddir}
WebUI assets: %{traefik_webuidir}

Install only the module packages you need, for example:
  traefik-core traefik-mod-docker traefik-mod-webui

Or install the "traefik" meta-package for the full set.
See MODULES_REPORT.md in the source for architecture details.
EOF

%files
%doc %{_docdir}/traefik/MODULES.txt

%files core
%{_bindir}/traefik
%{_sysusersdir}/%{name}.conf
%{_unitdir}/%{name}.service
%dir %{_sysconfdir}/traefik
%dir %{_sysconfdir}/traefik/conf.d
%dir %{traefik_moddir}
%config(noreplace) %{_sysconfdir}/traefik/traefik.yml
%config(noreplace) %{_sysconfdir}/logrotate.d/traefik
%config(noreplace) %verify(not md5 size mtime) %attr(600,traefik,traefik) /srv/traefik/acme.json
%config(noreplace) %verify(not md5 size mtime) %{_sysconfdir}/sysconfig/traefik
%dir %attr(755,traefik,traefik) /srv/traefik
%dir %{_localstatedir}/log/traefik

%files mod-docker
%{traefik_moddir}/traefik-docker.so
%{traefik_moddir}/traefik-swarm.so

%files mod-kubernetes
%{traefik_moddir}/traefik-kubernetes-crd.so
%{traefik_moddir}/traefik-kubernetes-ingress.so
%{traefik_moddir}/traefik-kubernetes-gateway.so
%{traefik_moddir}/traefik-kubernetes-ingress-nginx.so
%{traefik_moddir}/traefik-knative.so

%files mod-consul
%{traefik_moddir}/traefik-consul-catalog.so
%{traefik_moddir}/traefik-consul.so

%files mod-nomad
%{traefik_moddir}/traefik-nomad.so

%files mod-etcd
%{traefik_moddir}/traefik-etcd.so

%files mod-redis
%{traefik_moddir}/traefik-redis.so

%files mod-zookeeper
%{traefik_moddir}/traefik-zookeeper.so

%files mod-ecs
%{traefik_moddir}/traefik-ecs.so

%files mod-webui
%{traefik_moddir}/traefik-webui.so
%dir %{_datadir}/traefik
%{traefik_webuidir}/
