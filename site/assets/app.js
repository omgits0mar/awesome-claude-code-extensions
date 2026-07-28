(() => {
  "use strict";

  const PAGE_SIZE = 36;
  const CATALOG_URL = "./catalog/catalog.json";
  const METADATA_URL = "./github-metadata.json";

  const KIND_GROUPS = {
    all: null,
    plugin: ["plugin"],
    "mcp-server": ["mcp-server"],
    skills: ["skill", "command", "hook"],
    agents: ["agent", "workflow"],
    tools: [
      "tool",
      "interface",
      "monitoring",
      "mcp-tooling",
      "learning",
      "collection",
    ],
  };

  const KIND_LABELS = {
    plugin: "Plugin",
    skill: "Skill",
    command: "Command",
    hook: "Hook",
    agent: "Agent",
    workflow: "Workflow",
    "mcp-server": "MCP server",
    "mcp-tooling": "MCP tooling",
    interface: "Interface",
    monitoring: "Monitoring",
    learning: "Learning",
    tool: "Tool",
    collection: "Collection",
  };

  const KIND_GROUP_LABELS = {
    all: "All extensions",
    plugin: "Plugins",
    "mcp-server": "MCP servers",
    skills: "Skills, commands & hooks",
    agents: "Agents & workflows",
    tools: "Tools, interfaces & collections",
  };

  const TIER_LABELS = {
    official: "Official directory",
    popular: "Popular source",
    curated: "Curated",
    community: "Community",
  };

  const TIER_RANK = {
    official: 0,
    popular: 1,
    curated: 2,
    community: 3,
  };

  const IGNORED_TOPIC_TAGS = new Set([
    "claude-code",
    "mcp",
    "plugin",
    "plugins",
    "skill",
    "skills",
  ]);

  const CATEGORY_ALIASES = {
    database: "Databases",
    databases: "Databases",
    "developer tools": "Developer tools",
    "development tools": "Developer tools",
    security: "Security",
    "cloud platform": "Cloud platforms",
    "cloud platforms": "Cloud platforms",
    "browser automation": "Browser automation",
    "coding agents": "Coding agents",
    "data science tools": "Data science",
    "data science": "Data science",
    "art & culture": "Art & culture",
  };

  const state = {
    query: "",
    kind: "all",
    tier: "all",
    category: "all",
    stars: "all",
    officialOnly: false,
    licenseOnly: false,
    sort: "featured",
    visibleCount: PAGE_SIZE,
  };

  const data = {
    entries: [],
    counts: null,
    generatedAt: null,
    metadata: new Map(),
    metadataGeneratedAt: null,
    metadataRequested: 0,
    metadataFailed: 0,
    categoryLabels: new Map(),
  };

  const collator = new Intl.Collator(undefined, {
    numeric: true,
    sensitivity: "base",
  });
  const compactNumber = new Intl.NumberFormat(undefined, {
    notation: "compact",
    maximumFractionDigits: 1,
  });
  const wholeNumber = new Intl.NumberFormat();
  const desktopFilters = window.matchMedia("(min-width: 721px)");

  const elements = {
    search: document.querySelector("#search-input"),
    searchShortcut: document.querySelector(".search-shortcut"),
    kindChips: document.querySelector("#kind-chips"),
    filterToggle: document.querySelector("#filter-toggle"),
    filterPanel: document.querySelector("#filter-panel"),
    filterCount: document.querySelector("#filter-count"),
    tier: document.querySelector("#tier-filter"),
    category: document.querySelector("#category-filter"),
    stars: document.querySelector("#stars-filter"),
    starsCoverage: document.querySelector("#stars-coverage"),
    sort: document.querySelector("#sort-select"),
    official: document.querySelector("#official-filter"),
    license: document.querySelector("#license-filter"),
    clear: document.querySelector("#clear-filters"),
    results: document.querySelector("#catalog-results"),
    resultsTitle: document.querySelector("#results-title"),
    resultsCopy: document.querySelector("#results-copy"),
    activeFilters: document.querySelector("#active-filters"),
    metadataNote: document.querySelector("#metadata-note"),
    empty: document.querySelector("#empty-state"),
    emptyClear: document.querySelector("#empty-clear"),
    loadMore: document.querySelector("#load-more"),
    toast: document.querySelector("#toast"),
    catalogDate: document.querySelector("#catalog-date"),
    pulse: document.querySelector("#catalog-pulse"),
    pulseSummary: document.querySelector("#pulse-summary"),
  };

  let renderFrame = 0;
  let toastTimer = 0;
  let mobileFiltersOpen = false;

  function normalize(value) {
    return String(value || "")
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase()
      .replace(/\s+/g, " ")
      .trim();
  }

  function canonicalRepositoryUrl(value) {
    try {
      const url = new URL(value);
      if (url.protocol !== "https:" || url.hostname.toLowerCase() !== "github.com") {
        return "";
      }
      const parts = url.pathname
        .split("/")
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => decodeURIComponent(part));
      if (parts.length !== 2) {
        return "";
      }
      parts[1] = parts[1].replace(/\.git$/i, "");
      return `https://github.com/${parts[0].toLowerCase()}/${parts[1].toLowerCase()}`;
    } catch {
      return "";
    }
  }

  function repositoryParts(value) {
    try {
      const url = new URL(value);
      const [owner = "", repository = ""] = url.pathname
        .split("/")
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => decodeURIComponent(part));
      return {
        owner,
        repository: repository.replace(/\.git$/i, ""),
        label: owner && repository ? `${owner}/${repository.replace(/\.git$/i, "")}` : "",
      };
    } catch {
      return { owner: "", repository: "", label: "" };
    }
  }

  function categoryIdentity(value) {
    const stripped = String(value || "")
      .replace(/^[^\p{L}\p{N}]+/u, "")
      .replace(/[_-]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
    const key = normalize(stripped);
    const label =
      CATEGORY_ALIASES[key] ||
      (stripped ? stripped.charAt(0).toLocaleUpperCase() + stripped.slice(1) : "Other");
    return { key: normalize(label), label };
  }

  function safeGitHubUrl(value) {
    try {
      const url = new URL(value);
      if (url.protocol === "https:" && url.hostname.toLowerCase() === "github.com") {
        return url.href;
      }
    } catch {
      // Invalid URLs are rendered without a navigable target.
    }
    return "https://github.com/omgits0mar/awesome-claude-code-extensions";
  }

  function safeAvatarUrl(value) {
    try {
      const url = new URL(value);
      const host = url.hostname.toLowerCase();
      const allowed =
        host === "github.com" ||
        host === "avatars.githubusercontent.com" ||
        host.endsWith(".githubusercontent.com");
      if (url.protocol !== "https:" || !allowed) return "";
      if (host === "avatars.githubusercontent.com") {
        url.searchParams.set("s", "96");
      }
      return url.href;
    } catch {
      return "";
    }
  }

  function numberOrNull(value) {
    if (value === null || value === undefined || value === "") {
      return null;
    }
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function metadataRecord(raw) {
    const owner = raw?.owner || {};
    const language = raw?.primaryLanguage || raw?.primary_language || null;
    const license = raw?.licenseInfo || raw?.license_info || null;
    return {
      stars: numberOrNull(
        raw?.stargazerCount ?? raw?.stargazer_count ?? raw?.stars,
      ),
      forks: numberOrNull(raw?.forkCount ?? raw?.fork_count ?? raw?.forks),
      archived: Boolean(raw?.isArchived ?? raw?.is_archived),
      disabled: Boolean(raw?.isDisabled ?? raw?.is_disabled),
      fork: Boolean(raw?.isFork ?? raw?.is_fork),
      pushedAt: raw?.pushedAt ?? raw?.pushed_at ?? null,
      updatedAt: raw?.updatedAt ?? raw?.updated_at ?? null,
      avatarUrl:
        owner?.avatarUrl ??
        owner?.avatar_url ??
        raw?.ownerAvatarUrl ??
        raw?.owner_avatar_url ??
        null,
      openGraphImageUrl:
        raw?.openGraphImageUrl ?? raw?.open_graph_image_url ?? null,
      language:
        typeof language === "string" ? language : language?.name ?? null,
      languageColor:
        typeof language === "object" ? language?.color ?? null : null,
      license:
        typeof license === "string"
          ? license
          : license?.spdxId ?? license?.spdx_id ?? null,
    };
  }

  function indexEntry(entry) {
    const repository = repositoryParts(entry.repository_url);
    const category = categoryIdentity(entry.category);
    const aliases = Array.isArray(entry.aliases) ? entry.aliases : [];
    const tags = Array.isArray(entry.tags) ? entry.tags : [];
    const compatibility = Array.isArray(entry.compatibility)
      ? entry.compatibility
      : [];
    const sources = Array.isArray(entry.sources)
      ? entry.sources.map((source) => source?.name || "")
      : [];
    const searchText = [
      entry.name,
      ...aliases,
      entry.description,
      entry.category,
      ...tags,
      entry.author,
      repository.label,
      repository.owner,
      ...compatibility,
      ...sources,
    ];

    return {
      ...entry,
      _name: normalize(entry.name),
      _aliases: normalize(aliases.join(" ")),
      _description: normalize(entry.description),
      _tags: normalize(tags.join(" ")),
      _repository: normalize(repository.label),
      _search: normalize(searchText.filter(Boolean).join(" ")),
      _repositoryKey: canonicalRepositoryUrl(entry.repository_url),
      _owner: repository.owner,
      _repositoryName: repository.repository,
      _repositoryLabel: repository.label,
      _categoryKey: category.key,
      _categoryLabel: category.label,
    };
  }

  function metadataFor(entry) {
    return data.metadata.get(entry._repositoryKey) || null;
  }

  function readUrlState() {
    const params = new URLSearchParams(window.location.search);
    const kind = params.get("kind");
    const tier = params.get("tier");
    const stars = params.get("stars");
    const sort = params.get("sort");

    state.query = params.get("q") || "";
    state.kind = Object.hasOwn(KIND_GROUPS, kind) ? kind : "all";
    state.tier = Object.hasOwn(TIER_LABELS, tier) ? tier : "all";
    state.category = params.get("category") || "all";
    state.stars = ["10", "100", "1000", "10000"].includes(stars)
      ? stars
      : "all";
    state.officialOnly = params.get("official") === "1";
    state.licenseOnly = params.get("license") === "1";
    state.sort = ["featured", "stars", "name", "updated"].includes(sort)
      ? sort
      : "featured";
  }

  function syncUrl() {
    const params = new URLSearchParams();
    if (state.query) params.set("q", state.query);
    if (state.kind !== "all") params.set("kind", state.kind);
    if (state.tier !== "all") params.set("tier", state.tier);
    if (state.category !== "all") params.set("category", state.category);
    if (state.stars !== "all") params.set("stars", state.stars);
    if (state.officialOnly) params.set("official", "1");
    if (state.licenseOnly) params.set("license", "1");
    if (state.sort !== "featured") params.set("sort", state.sort);
    const query = params.toString();
    const target = `${window.location.pathname}${query ? `?${query}` : ""}`;
    try {
      window.history.replaceState(null, "", target);
    } catch {
      // A local file preview may not permit history state changes.
    }
  }

  async function fetchJson(url, required = true) {
    try {
      const response = await fetch(url, {
        headers: { Accept: "application/json" },
        cache: required ? "default" : "no-cache",
      });
      if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      if (required) {
        throw new Error(`Could not load ${url}: ${error.message}`);
      }
      return null;
    }
  }

  async function loadData() {
    const [catalogPayload, metadataPayload] = await Promise.all([
      fetchJson(CATALOG_URL, true),
      fetchJson(METADATA_URL, false),
    ]);

    if (!catalogPayload || !Array.isArray(catalogPayload.entries)) {
      throw new Error("The catalog JSON does not contain an entries array.");
    }

    data.entries = catalogPayload.entries.map(indexEntry);
    data.counts = catalogPayload.counts || {};
    data.generatedAt = catalogPayload.generated_at || null;

    if (metadataPayload?.repositories) {
      Object.entries(metadataPayload.repositories).forEach(([url, raw]) => {
        const key = canonicalRepositoryUrl(url);
        if (key && raw) {
          data.metadata.set(key, metadataRecord(raw));
        }
      });
      data.metadataGeneratedAt = metadataPayload.generated_at || null;
      data.metadataRequested =
        Number(metadataPayload.counts?.requested) || data.metadata.size;
      data.metadataFailed = Number(metadataPayload.counts?.failed) || 0;
    }

    if (data.metadata.size === 0) {
      state.stars = "all";
      if (state.sort === "stars" || state.sort === "updated") {
        state.sort = "featured";
      }
    }

    buildCategoryOptions();
    updateCatalogHeader();
    syncControls();
    render();
  }

  function buildCategoryOptions() {
    const counts = new Map();
    data.entries.forEach((entry) => {
      if (!entry._categoryKey) return;
      counts.set(entry._categoryKey, (counts.get(entry._categoryKey) || 0) + 1);
      if (!data.categoryLabels.has(entry._categoryKey)) {
        data.categoryLabels.set(entry._categoryKey, entry._categoryLabel);
      }
    });

    const options = Array.from(counts.entries()).sort((a, b) => {
      const labelA = data.categoryLabels.get(a[0]) || a[0];
      const labelB = data.categoryLabels.get(b[0]) || b[0];
      return collator.compare(labelA, labelB);
    });
    const fragment = document.createDocumentFragment();

    options.forEach(([key, count]) => {
      const option = document.createElement("option");
      option.value = key;
      option.textContent = `${data.categoryLabels.get(key) || key} (${wholeNumber.format(count)})`;
      fragment.append(option);
    });
    elements.category.append(fragment);

    if (state.category !== "all" && !counts.has(state.category)) {
      state.category = "all";
    }
  }

  function countKinds(kinds) {
    if (!kinds) return data.entries.length;
    const wanted = new Set(kinds);
    return data.entries.reduce(
      (count, entry) => count + (wanted.has(entry.kind) ? 1 : 0),
      0,
    );
  }

  function updateCatalogHeader() {
    const counts = data.counts || {};
    const byKind = counts.by_kind || {};
    const total = Number(counts.total) || data.entries.length;
    const repositoryCount =
      Number(counts.github_repositories) ||
      new Set(data.entries.map((entry) => entry._repositoryKey)).size;

    setText("#stat-total", wholeNumber.format(total));
    setText("#stat-repositories", wholeNumber.format(repositoryCount));
    setText("#stat-mcp", wholeNumber.format(byKind["mcp-server"] || 0));
    setText("#stat-plugins", wholeNumber.format(byKind.plugin || 0));
    setText(
      "#stat-official",
      wholeNumber.format(counts.official_directory || 0),
    );

    setText("#count-all", compactNumber.format(total));
    Object.entries(KIND_GROUPS).forEach(([group, kinds]) => {
      if (group === "all") return;
      setText(`#count-${group}`, compactNumber.format(countKinds(kinds)));
    });

    const pulseGroups = [
      {
        label: "MCP",
        value: byKind["mcp-server"] || 0,
        color: "#56c8f5",
      },
      {
        label: "Plugins & skills",
        value:
          (byKind.plugin || 0) +
          (byKind.skill || 0) +
          (byKind.command || 0) +
          (byKind.hook || 0),
        color: "#b07cff",
      },
      {
        label: "Agents & workflows",
        value: (byKind.agent || 0) + (byKind.workflow || 0),
        color: "#f6b35a",
      },
      {
        label: "Tools & interfaces",
        value:
          (byKind.tool || 0) +
          (byKind.interface || 0) +
          (byKind.monitoring || 0) +
          (byKind["mcp-tooling"] || 0),
        color: "#ed80b8",
      },
      {
        label: "Learning & collections",
        value: (byKind.learning || 0) + (byKind.collection || 0),
        color: "#34d399",
      },
    ];

    elements.pulse.replaceChildren();
    pulseGroups.forEach((group) => {
      const segment = document.createElement("span");
      segment.className = "pulse-segment";
      segment.style.setProperty("--share", `${(group.value / total) * 100}%`);
      segment.style.setProperty("--segment", group.color);
      segment.title = `${group.label}: ${wholeNumber.format(group.value)}`;
      elements.pulse.append(segment);
    });

    const mcpShare = total
      ? Math.round(((byKind["mcp-server"] || 0) / total) * 100)
      : 0;
    elements.pulseSummary.textContent = `${mcpShare}% MCP · ${Object.keys(byKind).length} artifact types`;
    elements.catalogDate.textContent = formatDate(data.generatedAt, {
      dateStyle: "medium",
    });

    const known = data.metadata.size;
    elements.stars.disabled = known === 0;
    elements.starsCoverage.textContent = known
      ? `${compactNumber.format(known)} repos`
      : "unavailable";

    const dot = elements.metadataNote.querySelector(".status-dot");
    const copy = elements.metadataNote.querySelector("span:last-child");
    dot.classList.remove("is-loading", "is-muted");
    if (known) {
      const coverage = data.metadataRequested
        ? ` · ${wholeNumber.format(known)} of ${wholeNumber.format(data.metadataRequested)} repos`
        : "";
      copy.textContent = `Stars updated ${formatDate(data.metadataGeneratedAt, {
        month: "short",
        day: "numeric",
      })}${coverage}`;
    } else {
      dot.classList.add("is-muted");
      copy.textContent = "Star data is added by the Pages build";
    }
  }

  function setText(selector, value) {
    const element = document.querySelector(selector);
    if (element) element.textContent = value;
  }

  function formatDate(value, options) {
    if (!value) return "unknown";
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return "unknown";
    return new Intl.DateTimeFormat(undefined, {
      timeZone: "UTC",
      ...options,
    }).format(parsed);
  }

  function scoreEntry(entry, query, tokens) {
    if (!query) return 0;
    let score = 0;

    if (entry._name === query) score += 180;
    else if (entry._name.startsWith(query)) score += 105;
    else if (entry._name.includes(query)) score += 75;

    if (entry._aliases.includes(query)) score += 55;
    if (entry._repository.includes(query)) score += 45;
    if (entry._tags.includes(query)) score += 36;
    if (normalize(entry.category).includes(query)) score += 25;
    if (entry._description.includes(query)) score += 14;

    tokens.forEach((token) => {
      if (entry._name.startsWith(token)) score += 16;
      else if (entry._name.includes(token)) score += 10;
      if (entry._tags.includes(token)) score += 5;
    });
    return score;
  }

  function filteredEntries() {
    const query = normalize(state.query);
    const tokens = query.split(" ").filter(Boolean);
    const kinds = KIND_GROUPS[state.kind];
    const minimumStars =
      state.stars === "all" ? null : Number.parseInt(state.stars, 10);

    const matches = data.entries.filter((entry) => {
      if (tokens.length && !tokens.every((token) => entry._search.includes(token))) {
        return false;
      }
      if (kinds && !kinds.includes(entry.kind)) return false;
      if (state.tier !== "all" && entry.source_tier !== state.tier) return false;
      if (
        state.category !== "all" &&
        entry._categoryKey !== state.category
      ) {
        return false;
      }
      if (state.officialOnly && !entry.official) return false;
      if (state.licenseOnly && !entry.license_verified) return false;
      if (minimumStars !== null) {
        const stars = metadataFor(entry)?.stars;
        if (stars === null || stars === undefined || stars < minimumStars) {
          return false;
        }
      }
      entry._score = scoreEntry(entry, query, tokens);
      return true;
    });

    const effectiveSort =
      state.sort === "featured" && query ? "relevance" : state.sort;

    matches.sort((a, b) => {
      const metaA = metadataFor(a);
      const metaB = metadataFor(b);
      const starsA = metaA?.stars ?? -1;
      const starsB = metaB?.stars ?? -1;

      if (effectiveSort === "relevance" && b._score !== a._score) {
        return b._score - a._score;
      }
      if (effectiveSort === "stars" && starsB !== starsA) {
        return starsB - starsA;
      }
      if (effectiveSort === "updated") {
        const updatedA = Date.parse(metaA?.pushedAt || "") || 0;
        const updatedB = Date.parse(metaB?.pushedAt || "") || 0;
        if (updatedB !== updatedA) return updatedB - updatedA;
      }
      if (effectiveSort === "featured") {
        const tierDifference =
          (TIER_RANK[a.source_tier] ?? 9) - (TIER_RANK[b.source_tier] ?? 9);
        if (tierDifference !== 0) return tierDifference;
        if (a.official !== b.official) return a.official ? -1 : 1;
        if (starsB !== starsA) return starsB - starsA;
      }
      const nameDifference = collator.compare(a.name, b.name);
      return nameDifference || collator.compare(a.id, b.id);
    });

    return matches;
  }

  function scheduleRender(resetVisible = true) {
    if (resetVisible) state.visibleCount = PAGE_SIZE;
    if (renderFrame) window.cancelAnimationFrame(renderFrame);
    renderFrame = window.requestAnimationFrame(() => {
      renderFrame = 0;
      render();
    });
  }

  function render() {
    syncControls();
    syncUrl();

    const matches = filteredEntries();
    const visible = matches.slice(0, state.visibleCount);
    const repositoryCount = new Set(matches.map((entry) => entry._repositoryKey))
      .size;
    const fragment = document.createDocumentFragment();
    visible.forEach((entry) => fragment.append(createCard(entry)));

    elements.results.replaceChildren(fragment);
    elements.results.classList.remove("is-loading");
    elements.results.setAttribute("aria-busy", "false");
    elements.resultsTitle.textContent = state.query
      ? `Results for “${state.query}”`
      : KIND_GROUP_LABELS[state.kind];
    elements.resultsCopy.textContent = matches.length
      ? `Showing ${wholeNumber.format(visible.length)} of ${wholeNumber.format(matches.length)} extensions across ${wholeNumber.format(repositoryCount)} repositories.`
      : "No matching extensions in the current catalog.";

    elements.empty.hidden = matches.length !== 0;
    elements.results.hidden = matches.length === 0;
    elements.loadMore.hidden = visible.length >= matches.length;
    if (!elements.loadMore.hidden) {
      const remaining = matches.length - visible.length;
      elements.loadMore.firstChild.textContent = `Load ${wholeNumber.format(
        Math.min(PAGE_SIZE, remaining),
      )} more `;
    }

    renderActiveFilters();
  }

  function createCard(entry) {
    const meta = metadataFor(entry);
    const targetUrl = safeGitHubUrl(entry.url);
    const article = document.createElement("article");
    article.className = "extension-card";
    article.dataset.kind = entry.kind;

    const cardLink = document.createElement("a");
    cardLink.className = "card-link";
    cardLink.href = targetUrl;
    cardLink.target = "_blank";
    cardLink.rel = "noopener noreferrer";
    cardLink.setAttribute("aria-label", `Open ${entry.name} on GitHub`);

    const head = document.createElement("div");
    head.className = "card-head";

    const avatar = document.createElement("div");
    avatar.className = "repo-avatar";
    avatar.style.setProperty(
      "--avatar-hue",
      String(hashString(entry._repositoryKey || entry.id) % 360),
    );
    const initials = document.createElement("span");
    initials.textContent = makeInitials(entry._owner || entry.name);
    initials.setAttribute("aria-hidden", "true");
    avatar.append(initials);

    const fallbackAvatar = entry._owner
      ? `https://github.com/${encodeURIComponent(entry._owner)}.png?size=96`
      : "";
    const avatarUrl = safeAvatarUrl(meta?.avatarUrl || fallbackAvatar);
    if (avatarUrl) {
      const image = document.createElement("img");
      image.src = avatarUrl;
      image.alt = "";
      image.width = 44;
      image.height = 44;
      image.loading = "lazy";
      image.decoding = "async";
      image.referrerPolicy = "no-referrer";
      image.addEventListener("load", () => image.classList.add("is-loaded"), {
        once: true,
      });
      image.addEventListener(
        "error",
        () => {
          image.remove();
        },
        { once: true },
      );
      avatar.append(image);
    }

    const titleWrap = document.createElement("div");
    titleWrap.className = "card-title-wrap";
    const title = document.createElement("span");
    title.className = "card-title";
    title.textContent = entry.name;
    title.title = entry.name;
    const repository = document.createElement("span");
    repository.className = "repo-name";
    repository.textContent = entry._repositoryLabel || "GitHub repository";
    repository.title = entry._repositoryLabel || entry.repository_url;
    titleWrap.append(title, repository);

    const external = document.createElement("span");
    external.className = "external-link";
    external.setAttribute("aria-hidden", "true");
    external.append(makeIcon("external"));
    head.append(avatar, titleWrap, external);

    const description = document.createElement("p");
    description.className = "card-description";
    description.textContent = entry.description;
    description.title = entry.description;

    const badges = document.createElement("div");
    badges.className = "badge-row";
    badges.append(
      makeBadge(KIND_LABELS[entry.kind] || entry.kind, "kind"),
      makeBadge(
        TIER_LABELS[entry.source_tier] || entry.source_tier,
        `tier-${entry.source_tier}`,
      ),
    );
    if (entry.official && entry.source_tier !== "official") {
      badges.append(makeBadge("First-party", "verified"));
    }
    if (entry.license_verified) {
      badges.append(makeBadge("License checked", "verified"));
    }
    if (meta?.archived || meta?.disabled) {
      badges.append(makeBadge(meta.disabled ? "Disabled" : "Archived", "archived"));
    }

    const topics = document.createElement("div");
    topics.className = "tag-row";
    const topicValues = [
      entry._categoryLabel,
      ...(Array.isArray(entry.tags) ? entry.tags : []),
    ]
      .filter(Boolean)
      .filter((value, index, all) => {
        const key = normalize(value);
        return (
          !IGNORED_TOPIC_TAGS.has(key) &&
          all.findIndex((candidate) => normalize(candidate) === key) === index
        );
      })
      .slice(0, 3);
    topicValues.forEach((value) => {
      const topic = document.createElement("span");
      topic.className = "topic-tag";
      topic.textContent = value;
      topic.title = value;
      topics.append(topic);
    });

    const footer = document.createElement("div");
    footer.className = "card-footer";
    const starSignal = document.createElement("span");
    starSignal.className = `repo-signal${meta?.stars !== null && meta?.stars !== undefined ? " has-data" : ""}`;
    starSignal.append(makeIcon("star"));
    const starText = document.createElement("span");
    starText.textContent =
      meta?.stars !== null && meta?.stars !== undefined
        ? compactNumber.format(meta.stars)
        : "—";
    starSignal.title =
      meta?.stars !== null && meta?.stars !== undefined
        ? `${wholeNumber.format(meta.stars)} GitHub stars`
        : "GitHub star count unavailable";
    starSignal.append(starText);
    footer.append(starSignal);

    const license = document.createElement("span");
    license.className = "license-signal";
    license.textContent = entry.license_verified
      ? entry.license
      : meta?.license && meta.license !== "NOASSERTION"
        ? `GitHub: ${meta.license}`
        : "License unchecked";
    license.title = license.textContent;
    footer.append(license);

    const installCommand =
      entry.install ||
      (Array.isArray(entry.install_commands) ? entry.install_commands[0] : null);
    if (installCommand) {
      const copy = document.createElement("button");
      copy.className = "copy-install";
      copy.type = "button";
      copy.dataset.command = installCommand;
      copy.setAttribute("aria-label", `Copy install command for ${entry.name}`);
      copy.title = installCommand;
      copy.append(makeIcon("copy"), document.createTextNode("Copy command"));
      footer.append(copy);
    }

    article.append(cardLink, head, description, badges, topics, footer);
    return article;
  }

  function makeBadge(text, className) {
    const badge = document.createElement("span");
    badge.className = `entry-badge ${className}`;
    badge.textContent = text;
    return badge;
  }

  function makeIcon(name) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("aria-hidden", "true");

    if (name === "star") {
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute(
        "d",
        "m12 2.9 2.72 5.5 6.08.89-4.4 4.28 1.04 6.05L12 16.76l-5.44 2.86 1.04-6.05-4.4-4.28 6.08-.89L12 2.9Z",
      );
      svg.append(path);
    } else if (name === "copy") {
      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", "8");
      rect.setAttribute("y", "8");
      rect.setAttribute("width", "11");
      rect.setAttribute("height", "11");
      rect.setAttribute("rx", "2");
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", "M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2");
      svg.append(rect, path);
    } else {
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", "M14 5h5v5M19 5l-8 8M18 13v5a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5");
      svg.append(path);
    }
    return svg;
  }

  function hashString(value) {
    let hash = 2166136261;
    for (let index = 0; index < value.length; index += 1) {
      hash ^= value.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
  }

  function makeInitials(value) {
    const words = String(value || "?")
      .replace(/[^a-zA-Z0-9]+/g, " ")
      .trim()
      .split(/\s+/)
      .filter(Boolean);
    if (!words.length) return "?";
    if (words.length === 1) return words[0].slice(0, 2).toLocaleUpperCase();
    return `${words[0][0]}${words[1][0]}`.toLocaleUpperCase();
  }

  function syncControls() {
    if (elements.search.value !== state.query) {
      elements.search.value = state.query;
    }
    elements.tier.value = state.tier;
    elements.category.value = state.category;
    elements.stars.value = state.stars;
    elements.sort.value = state.sort;
    elements.official.checked = state.officialOnly;
    elements.license.checked = state.licenseOnly;

    elements.kindChips.querySelectorAll("[data-kind]").forEach((button) => {
      const active = button.dataset.kind === state.kind;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });

    const filterCount = [
      state.kind !== "all",
      state.tier !== "all",
      state.category !== "all",
      state.stars !== "all",
      state.officialOnly,
      state.licenseOnly,
    ].filter(Boolean).length;
    elements.filterCount.hidden = filterCount === 0;
    elements.filterCount.textContent = String(filterCount);
  }

  function renderActiveFilters() {
    const filters = [];
    if (state.query) {
      filters.push({ key: "query", label: `Search: ${state.query}` });
    }
    if (state.kind !== "all") {
      filters.push({ key: "kind", label: KIND_GROUP_LABELS[state.kind] });
    }
    if (state.tier !== "all") {
      filters.push({ key: "tier", label: TIER_LABELS[state.tier] });
    }
    if (state.category !== "all") {
      filters.push({
        key: "category",
        label: data.categoryLabels.get(state.category) || state.category,
      });
    }
    if (state.stars !== "all") {
      filters.push({
        key: "stars",
        label: `${wholeNumber.format(Number(state.stars))}+ stars`,
      });
    }
    if (state.officialOnly) {
      filters.push({ key: "official", label: "First-party" });
    }
    if (state.licenseOnly) {
      filters.push({ key: "license", label: "License checked" });
    }

    const fragment = document.createDocumentFragment();
    filters.forEach((filter) => {
      const item = document.createElement("span");
      item.className = "active-filter";
      item.append(document.createTextNode(filter.label));
      const clear = document.createElement("button");
      clear.type = "button";
      clear.dataset.clear = filter.key;
      clear.textContent = "×";
      clear.setAttribute("aria-label", `Remove ${filter.label} filter`);
      item.append(clear);
      fragment.append(item);
    });
    elements.activeFilters.replaceChildren(fragment);
  }

  function clearFilter(key) {
    if (key === "query") state.query = "";
    if (key === "kind") state.kind = "all";
    if (key === "tier") state.tier = "all";
    if (key === "category") state.category = "all";
    if (key === "stars") state.stars = "all";
    if (key === "official") state.officialOnly = false;
    if (key === "license") state.licenseOnly = false;
    scheduleRender(true);
  }

  function resetState() {
    Object.assign(state, {
      query: "",
      kind: "all",
      tier: "all",
      category: "all",
      stars: "all",
      officialOnly: false,
      licenseOnly: false,
      sort: "featured",
      visibleCount: PAGE_SIZE,
    });
    scheduleRender(true);
  }

  function updateFilterPanel() {
    const open = desktopFilters.matches || mobileFiltersOpen;
    elements.filterPanel.classList.toggle("is-open", open);
    elements.filterPanel.toggleAttribute("inert", !open);
    elements.filterPanel.setAttribute("aria-hidden", String(!open));
    elements.filterToggle.setAttribute("aria-expanded", String(open));
  }

  function showToast(message) {
    window.clearTimeout(toastTimer);
    elements.toast.textContent = message;
    elements.toast.classList.add("is-visible");
    toastTimer = window.setTimeout(() => {
      elements.toast.classList.remove("is-visible");
    }, 2600);
  }

  async function copyText(value) {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      return;
    }
    const textarea = document.createElement("textarea");
    textarea.value = value;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.append(textarea);
    textarea.select();
    const copied = document.execCommand("copy");
    textarea.remove();
    if (!copied) throw new Error("Copy command was rejected.");
  }

  function showLoadError(error) {
    elements.results.classList.remove("is-loading");
    elements.results.setAttribute("aria-busy", "false");
    elements.results.replaceChildren();
    elements.results.hidden = true;
    elements.resultsTitle.textContent = "Catalog unavailable";
    elements.resultsCopy.textContent =
      "The generated catalog could not be loaded. If you opened this file directly, serve the built site over HTTP.";
    elements.empty.hidden = false;
    elements.empty.querySelector("h2").textContent = "Could not load the catalog";
    elements.empty.querySelector("p").textContent = error.message;
    elements.emptyClear.hidden = true;
    const dot = elements.metadataNote.querySelector(".status-dot");
    dot.classList.remove("is-loading");
    dot.classList.add("is-muted");
    elements.metadataNote.querySelector("span:last-child").textContent =
      "Data load failed";
  }

  function bindEvents() {
    elements.search.addEventListener("input", (event) => {
      state.query = event.target.value.trimStart();
      scheduleRender(true);
    });

    elements.kindChips.addEventListener("click", (event) => {
      const button = event.target.closest("[data-kind]");
      if (!button || !Object.hasOwn(KIND_GROUPS, button.dataset.kind)) return;
      state.kind = button.dataset.kind;
      scheduleRender(true);
    });

    elements.tier.addEventListener("change", (event) => {
      state.tier = event.target.value;
      scheduleRender(true);
    });
    elements.category.addEventListener("change", (event) => {
      state.category = event.target.value;
      scheduleRender(true);
    });
    elements.stars.addEventListener("change", (event) => {
      state.stars = event.target.value;
      scheduleRender(true);
    });
    elements.sort.addEventListener("change", (event) => {
      state.sort = event.target.value;
      scheduleRender(true);
    });
    elements.official.addEventListener("change", (event) => {
      state.officialOnly = event.target.checked;
      scheduleRender(true);
    });
    elements.license.addEventListener("change", (event) => {
      state.licenseOnly = event.target.checked;
      scheduleRender(true);
    });

    elements.clear.addEventListener("click", resetState);
    elements.emptyClear.addEventListener("click", resetState);
    elements.loadMore.addEventListener("click", () => {
      state.visibleCount += PAGE_SIZE;
      scheduleRender(false);
    });

    elements.filterToggle.addEventListener("click", () => {
      mobileFiltersOpen = !mobileFiltersOpen;
      updateFilterPanel();
    });

    elements.activeFilters.addEventListener("click", (event) => {
      const clear = event.target.closest("[data-clear]");
      if (clear) clearFilter(clear.dataset.clear);
    });

    elements.results.addEventListener("click", async (event) => {
      const button = event.target.closest(".copy-install");
      if (!button) return;
      try {
        const command = button.dataset.command || "";
        await copyText(command);
        showToast(`Copied: ${command}`);
      } catch {
        showToast("Could not copy the install command");
      }
    });

    document.addEventListener("keydown", (event) => {
      const target = event.target;
      const isTyping =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement ||
        target?.isContentEditable;
      if (
        (event.metaKey || event.ctrlKey) &&
        event.key.toLocaleLowerCase() === "k"
      ) {
        event.preventDefault();
        elements.search.focus();
        elements.search.select();
      } else if (event.key === "/" && !isTyping) {
        event.preventDefault();
        elements.search.focus();
      } else if (event.key === "Escape" && target === elements.search && state.query) {
        state.query = "";
        scheduleRender(true);
      }
    });

    const filterMediaChanged = () => {
      if (!desktopFilters.matches) mobileFiltersOpen = false;
      updateFilterPanel();
    };
    if (desktopFilters.addEventListener) {
      desktopFilters.addEventListener("change", filterMediaChanged);
    } else {
      desktopFilters.addListener(filterMediaChanged);
    }
  }

  function boot() {
    readUrlState();
    bindEvents();
    updateFilterPanel();
    const isMac = /Mac|iPhone|iPad/.test(navigator.platform);
    elements.searchShortcut.textContent = isMac ? "⌘ K" : "Ctrl K";
    loadData().catch(showLoadError);
  }

  boot();
})();
