import SwiftUI

struct MainAppView: View {
    @Bindable var session: AuthenticationSession
    let user: SeasonlyUser
    let logout: () -> Void

    @State private var selectedTab = MainTab.home
    @State private var recipes: [SeasonalRecipe] = []
    @State private var produce: [SeasonalProduce] = []
    @State private var favorites: [SeasonalRecipe] = []
    @State private var recentlyViewed: [SeasonalRecipe] = []
    @State private var plannedMeals: [PlannedMeal] = []
    @State private var selectedRecipe: SeasonalRecipe?
    @State private var planningRecipe: SeasonalRecipe?
    @State private var isLoading = false
    @State private var recipeErrorMessage: String?
    @State private var profilePresented = false

    private var countryCode: String? {
        session.onboardingProfile?.countryCode ?? user.profile?.countryCode
    }

    private var regionLabel: String {
        if let region = session.onboardingProfile?.regionCode ?? user.profile?.regionCode {
            return region
        }
        return countryCode ?? "Set location"
    }

    var body: some View {
        TabView(selection: $selectedTab) {
            HomeTabView(
                user: user,
                regionLabel: regionLabel,
                recipes: recipes,
                produce: produce,
                favorites: favorites,
                plannedMeals: plannedMeals,
                isLoading: isLoading,
                errorMessage: recipeErrorMessage,
                openRecipe: openRecipe,
                toggleFavorite: toggleFavorite,
                planRecipe: { planningRecipe = $0 },
                showProfile: { profilePresented = true }
            )
            .tabItem { Label("Home", systemImage: "house.fill") }
            .tag(MainTab.home)

            ExploreTabView(
                regionLabel: regionLabel,
                recipes: recipes,
                produce: produce,
                favorites: favorites,
                isLoading: isLoading,
                errorMessage: recipeErrorMessage,
                openRecipe: openRecipe,
                toggleFavorite: toggleFavorite,
                planRecipe: { planningRecipe = $0 }
            )
            .tabItem { Label("Explore", systemImage: "magnifyingglass") }
            .tag(MainTab.explore)

            PlannerTabView(
                plannedMeals: $plannedMeals,
                removePlannedMeal: removePlannedMeal,
                openRecipe: openRecipe
            )
            .tabItem { Label("Planner", systemImage: "calendar") }
            .tag(MainTab.planner)

            SavedTabView(
                favorites: $favorites,
                recentlyViewed: recentlyViewed,
                openRecipe: openRecipe,
                toggleFavorite: toggleFavorite,
                planRecipe: { planningRecipe = $0 }
            )
            .tabItem { Label("Saved", systemImage: "heart.fill") }
            .tag(MainTab.saved)
        }
        .tint(SeasonlyColors.brown)
        .task { await loadDashboardData() }
        .refreshable { await loadDashboardData() }
        .sheet(item: $selectedRecipe) { recipe in
            RecipeDetailView(
                recipe: recipe,
                regionLabel: regionLabel,
                isFavorite: favorites.contains(where: { $0.id == recipe.id }),
                toggleFavorite: { toggleFavorite(recipe) },
                planRecipe: { planningRecipe = recipe }
            )
        }
        .sheet(item: $planningRecipe) { recipe in
            PlannerSheet(recipe: recipe) { day, meal in
                addPlannedMeal(recipe: recipe, day: day, meal: meal)
            }
            .presentationDetents([.medium])
            .presentationDragIndicator(.visible)
        }
        .sheet(isPresented: $profilePresented) {
            ProfileSettingsView(
                session: session,
                user: user,
                profile: session.onboardingProfile,
                logout: logout
            )
            .presentationDetents([.large])
            .presentationDragIndicator(.visible)
        }
        .onChange(of: session.onboardingProfile?.updatedAt) {
            Task { await loadDashboardData() }
        }
    }

    private func loadDashboardData() async {
        guard !isLoading else { return }
        isLoading = true
        recipeErrorMessage = nil
        defer { isLoading = false }

        if let recipeList = await fetchPreferredSeasonalRecipes(pageSize: 24) {
            recipes = recipeList.items
            if recipeList.items.isEmpty {
                recipeErrorMessage = emptyRecipeMessage(for: recipeList)
            }
        } else {
            recipeErrorMessage = session.errorMessage ?? "Seasonal recipes could not be loaded."
        }
        if let countryCode {
            produce = await session.fetchSeasonalProduce(countryCode: countryCode)
        }

        favorites = await session.fetchFavourites()
        recentlyViewed = await session.fetchRecipeHistory()
        plannedMeals = await session.fetchPlannedMeals().compactMap(PlannedMeal.init(remote:))
    }

    private func fetchPreferredSeasonalRecipes(pageSize: Int) async -> SeasonalRecipeList? {
        let preferredAreas = selectedCuisineAreas
        guard !preferredAreas.isEmpty else {
            return await session.fetchSeasonalRecipes(pageSize: pageSize)
        }

        var countryCode = countryCode ?? "GB"
        var month = Calendar.current.component(.month, from: Date())
        var total = 0
        var mergedRecipes: [SeasonalRecipe] = []
        var seenRecipeIDs = Set<UUID>()

        for area in preferredAreas {
            guard let recipeList = await session.fetchSeasonalRecipes(pageSize: pageSize, area: area) else {
                continue
            }

            countryCode = recipeList.countryCode
            month = recipeList.month
            total += recipeList.total

            for recipe in recipeList.items where seenRecipeIDs.insert(recipe.id).inserted {
                mergedRecipes.append(recipe)
            }
        }

        mergedRecipes.sort { first, second in
            if first.matchedSeasonalProduceCount != second.matchedSeasonalProduceCount {
                return first.matchedSeasonalProduceCount > second.matchedSeasonalProduceCount
            }
            return first.name.localizedCaseInsensitiveCompare(second.name) == .orderedAscending
        }

        return SeasonalRecipeList(
            countryCode: countryCode,
            month: month,
            page: 1,
            pageSize: pageSize,
            total: total,
            items: Array(mergedRecipes.prefix(pageSize))
        )
    }

    private var selectedCuisineAreas: [String] {
        guard session.onboardingProfile?.cuisinePreferenceStatus == "provided" else { return [] }
        return session.onboardingProfile?.cuisineAreas ?? []
    }

    private func emptyRecipeMessage(for recipeList: SeasonalRecipeList) -> String {
        let cuisineText = selectedCuisineAreas.isEmpty ? "" : " matching \(selectedCuisineAreas.joined(separator: ", "))"
        return "The seasonal recipe endpoint returned 0 recipes using \(recipeList.countryCode) seasonal produce in month \(recipeList.month)\(cuisineText)."
    }

    private func openRecipe(_ recipe: SeasonalRecipe) {
        selectedRecipe = recipe
        recentlyViewed.removeAll { $0.id == recipe.id }
        recentlyViewed.insert(recipe, at: 0)
        recentlyViewed = Array(recentlyViewed.prefix(20))
        Task { await session.recordRecipeHistory(recipeId: recipe.id) }
    }

    private func toggleFavorite(_ recipe: SeasonalRecipe) {
        if favorites.contains(where: { $0.id == recipe.id }) {
            favorites.removeAll { $0.id == recipe.id }
            Task { await session.deleteFavourite(recipeId: recipe.id) }
        } else {
            favorites.insert(recipe, at: 0)
            Task { await session.saveFavourite(recipeId: recipe.id) }
        }
    }

    private func addPlannedMeal(recipe: SeasonalRecipe, day: Weekday, meal: MealSlot) {
        Task {
            guard let remoteMeal = await session.savePlannedMeal(
                recipeId: recipe.id,
                dayOfWeek: day.apiValue,
                mealSlot: meal.apiValue
            ), let plannedMeal = PlannedMeal(remote: remoteMeal) else { return }
            plannedMeals.removeAll { $0.id == plannedMeal.id }
            plannedMeals.append(plannedMeal)
        }
    }

    private func removePlannedMeal(_ meal: PlannedMeal) {
        plannedMeals.removeAll { $0.id == meal.id }
        Task { await session.deletePlannedMeal(id: meal.id) }
    }
}

private enum MainTab {
    case home
    case explore
    case planner
    case saved
}

struct PlannedMeal: Identifiable, Hashable {
    let id: UUID
    let recipe: SeasonalRecipe
    let day: Weekday
    let meal: MealSlot

    init(id: UUID = UUID(), recipe: SeasonalRecipe, day: Weekday, meal: MealSlot) {
        self.id = id
        self.recipe = recipe
        self.day = day
        self.meal = meal
    }

    init?(remote: RemotePlannedMeal) {
        guard let day = Weekday(apiValue: remote.dayOfWeek),
              let meal = MealSlot(apiValue: remote.mealSlot) else {
            return nil
        }
        self.init(id: remote.id, recipe: remote.recipe.seasonalRecipe, day: day, meal: meal)
    }
}

enum Weekday: String, CaseIterable, Identifiable {
    case monday = "Monday"
    case tuesday = "Tuesday"
    case wednesday = "Wednesday"
    case thursday = "Thursday"
    case friday = "Friday"
    case saturday = "Saturday"
    case sunday = "Sunday"

    var id: String { rawValue }

    var apiValue: Int {
        switch self {
        case .monday: return 1
        case .tuesday: return 2
        case .wednesday: return 3
        case .thursday: return 4
        case .friday: return 5
        case .saturday: return 6
        case .sunday: return 7
        }
    }

    init?(apiValue: Int) {
        switch apiValue {
        case 1: self = .monday
        case 2: self = .tuesday
        case 3: self = .wednesday
        case 4: self = .thursday
        case 5: self = .friday
        case 6: self = .saturday
        case 7: self = .sunday
        default: return nil
        }
    }
}

enum MealSlot: String, CaseIterable, Identifiable {
    case breakfast = "Breakfast"
    case lunch = "Lunch"
    case dinner = "Dinner"
    case snack = "Snack"

    var id: String { rawValue }

    var apiValue: String { rawValue.lowercased() }

    init?(apiValue: String) {
        switch apiValue {
        case "breakfast": self = .breakfast
        case "lunch": self = .lunch
        case "dinner": self = .dinner
        case "snack": self = .snack
        default: return nil
        }
    }
}

private struct HomeTabView: View {
    let user: SeasonlyUser
    let regionLabel: String
    let recipes: [SeasonalRecipe]
    let produce: [SeasonalProduce]
    let favorites: [SeasonalRecipe]
    let plannedMeals: [PlannedMeal]
    let isLoading: Bool
    let errorMessage: String?
    let openRecipe: (SeasonalRecipe) -> Void
    let toggleFavorite: (SeasonalRecipe) -> Void
    let planRecipe: (SeasonalRecipe) -> Void
    let showProfile: () -> Void

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    HomeHero(
                        displayName: user.profile?.displayName ?? user.email.components(separatedBy: "@").first ?? "there",
                        regionLabel: regionLabel,
                        primaryRecipe: recipes.first,
                        openRecipe: openRecipe,
                        surpriseRecipe: recipes.dropFirst().randomElement().map { recipe in
                            { openRecipe(recipe) }
                        }
                    )

                    ProduceStrip(regionLabel: regionLabel, produce: Array(produce.prefix(8)))

                    if let errorMessage {
                        StatusMessage(message: errorMessage, isError: true)
                    }

                    SectionHeader(title: "Recommended for you", actionTitle: "See all") {}
                    RecipeCarousel(
                        recipes: recipes,
                        favorites: favorites,
                        openRecipe: openRecipe,
                        toggleFavorite: toggleFavorite,
                        planRecipe: planRecipe
                    )

                    SectionHeader(title: "Your week", actionTitle: "Open planner") {}
                    WeekPreview(plannedMeals: plannedMeals)
                }
                .padding(18)
            }
            .background(AppBackground())
            .navigationTitle("Seasonly")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    LocationPill(regionLabel: regionLabel)
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button(action: showProfile) {
                        Image(systemName: "person.crop.circle.fill")
                            .font(.title2)
                            .foregroundStyle(SeasonlyColors.brown)
                    }
                    .accessibilityLabel("Profile and settings")
                }
            }
            .overlay {
                if isLoading && recipes.isEmpty {
                    ProgressView()
                        .tint(SeasonlyColors.brown)
                }
            }
        }
    }
}

private struct ExploreTabView: View {
    let regionLabel: String
    let recipes: [SeasonalRecipe]
    let produce: [SeasonalProduce]
    let favorites: [SeasonalRecipe]
    let isLoading: Bool
    let errorMessage: String?
    let openRecipe: (SeasonalRecipe) -> Void
    let toggleFavorite: (SeasonalRecipe) -> Void
    let planRecipe: (SeasonalRecipe) -> Void

    @State private var query = ""
    @State private var scope = ExploreScope.recipes
    @State private var inSeasonOnly = true

    private var filteredRecipes: [SeasonalRecipe] {
        recipes.filter { recipe in
            query.isEmpty || recipe.name.localizedCaseInsensitiveContains(query) || (recipe.area ?? "").localizedCaseInsensitiveContains(query)
        }
    }

    private var filteredProduce: [SeasonalProduce] {
        produce.filter { item in
            query.isEmpty || item.name.localizedCaseInsensitiveContains(query)
        }
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    LocationPill(regionLabel: regionLabel)

                    Picker("Explore", selection: $scope) {
                        ForEach(ExploreScope.allCases) { scope in
                            Text(scope.title).tag(scope)
                        }
                    }
                    .pickerStyle(.segmented)

                    Toggle("In season now", isOn: $inSeasonOnly)
                        .toggleStyle(.switch)
                        .font(.subheadline.weight(.semibold))

                    if let errorMessage {
                        StatusMessage(message: errorMessage, isError: true)
                    }

                    if scope == .recipes {
                        LazyVStack(spacing: 12) {
                            ForEach(filteredRecipes) { recipe in
                                RecipeListCard(
                                    recipe: recipe,
                                    isFavorite: favorites.contains(where: { $0.id == recipe.id }),
                                    openRecipe: { openRecipe(recipe) },
                                    toggleFavorite: { toggleFavorite(recipe) },
                                    planRecipe: { planRecipe(recipe) }
                                )
                            }
                        }
                    } else {
                        LazyVStack(spacing: 12) {
                            ForEach(filteredProduce) { item in
                                ProduceDetailCard(item: item, regionLabel: regionLabel)
                            }
                        }
                    }
                }
                .padding(18)
            }
            .background(AppBackground())
            .navigationTitle("Explore")
            .searchable(text: $query, prompt: "Search recipes or ingredients")
            .overlay {
                if isLoading && recipes.isEmpty {
                    ProgressView().tint(SeasonlyColors.brown)
                }
            }
        }
    }
}

private enum ExploreScope: CaseIterable, Identifiable {
    case recipes
    case produce

    var id: Self { self }
    var title: String { self == .recipes ? "Recipes" : "Seasonal ingredients" }
}

private struct PlannerTabView: View {
    @Binding var plannedMeals: [PlannedMeal]
    let removePlannedMeal: (PlannedMeal) -> Void
    let openRecipe: (SeasonalRecipe) -> Void

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    WeekPlannerHeader()

                    ForEach(Weekday.allCases) { day in
                        PlannerDayCard(
                            day: day,
                            meals: plannedMeals.filter { $0.day == day },
                            remove: removePlannedMeal,
                            openRecipe: openRecipe
                        )
                    }
                }
                .padding(18)
            }
            .background(AppBackground())
            .navigationTitle("Planner")
        }
    }
}

private struct SavedTabView: View {
    @Binding var favorites: [SeasonalRecipe]
    let recentlyViewed: [SeasonalRecipe]
    let openRecipe: (SeasonalRecipe) -> Void
    let toggleFavorite: (SeasonalRecipe) -> Void
    let planRecipe: (SeasonalRecipe) -> Void

    @State private var scope = SavedScope.favorites
    @State private var query = ""

    private var visibleRecipes: [SeasonalRecipe] {
        let source = scope == .favorites ? favorites : recentlyViewed
        return source.filter { query.isEmpty || $0.name.localizedCaseInsensitiveContains(query) }
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Picker("Saved recipes", selection: $scope) {
                        ForEach(SavedScope.allCases) { scope in
                            Text(scope.title).tag(scope)
                        }
                    }
                    .pickerStyle(.segmented)

                    if visibleRecipes.isEmpty {
                        EmptyState(
                            icon: scope == .favorites ? "heart" : "clock.arrow.circlepath",
                            title: scope == .favorites ? "No favourites yet" : "No recently viewed recipes",
                            message: "Recipes you save or open will appear here."
                        )
                    } else {
                        LazyVStack(spacing: 12) {
                            ForEach(visibleRecipes) { recipe in
                                RecipeListCard(
                                    recipe: recipe,
                                    isFavorite: favorites.contains(where: { $0.id == recipe.id }),
                                    openRecipe: { openRecipe(recipe) },
                                    toggleFavorite: { toggleFavorite(recipe) },
                                    planRecipe: { planRecipe(recipe) }
                                )
                            }
                        }
                    }
                }
                .padding(18)
            }
            .background(AppBackground())
            .navigationTitle("Saved")
            .searchable(text: $query, prompt: "Search saved recipes")
        }
    }
}

private enum SavedScope: CaseIterable, Identifiable {
    case favorites
    case recent

    var id: Self { self }
    var title: String { self == .favorites ? "Favourites" : "Recently viewed" }
}

private struct HomeHero: View {
    let displayName: String
    let regionLabel: String
    let primaryRecipe: SeasonalRecipe?
    let openRecipe: (SeasonalRecipe) -> Void
    let surpriseRecipe: (() -> Void)?

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text(greeting)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.secondary)

            Text("What should I cook today?")
                .font(.system(.largeTitle, design: .rounded, weight: .bold))
                .foregroundStyle(SeasonlyColors.ink)

            Text("Seasonal recipes matched to your location and dietary profile.")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            HStack(spacing: 12) {
                Button {
                    if let primaryRecipe { openRecipe(primaryRecipe) }
                } label: {
                    Label("Find a recipe", systemImage: "sparkles")
                        .frame(maxWidth: .infinity)
                        .frame(height: 48)
                }
                .buttonStyle(.borderedProminent)
                .tint(SeasonlyColors.brown)
                .disabled(primaryRecipe == nil)

                Button {
                    surpriseRecipe?()
                } label: {
                    Image(systemName: "shuffle")
                        .frame(width: 48, height: 48)
                }
                .buttonStyle(.bordered)
                .tint(SeasonlyColors.brown)
                .disabled(surpriseRecipe == nil)
                .accessibilityLabel("Surprise me")
            }
        }
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
        .overlay(alignment: .topTrailing) {
            Image(systemName: "leaf.fill")
                .font(.system(size: 44, weight: .bold))
                .foregroundStyle(SeasonlyColors.brown.opacity(0.16))
                .padding(20)
        }
    }

    private var greeting: String {
        "Good evening, \(displayName) • \(regionLabel)"
    }
}

private struct RecipeCarousel: View {
    let recipes: [SeasonalRecipe]
    let favorites: [SeasonalRecipe]
    let openRecipe: (SeasonalRecipe) -> Void
    let toggleFavorite: (SeasonalRecipe) -> Void
    let planRecipe: (SeasonalRecipe) -> Void

    var body: some View {
        if recipes.isEmpty {
            EmptyState(icon: "fork.knife", title: "No seasonal recipes yet", message: "Check your backend data import or try another month.")
        } else {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 14) {
                    ForEach(recipes.prefix(8)) { recipe in
                        RecipeCard(
                            recipe: recipe,
                            isFavorite: favorites.contains(where: { $0.id == recipe.id }),
                            openRecipe: { openRecipe(recipe) },
                            toggleFavorite: { toggleFavorite(recipe) },
                            planRecipe: { planRecipe(recipe) }
                        )
                    }
                }
                .padding(.vertical, 2)
            }
        }
    }
}

private struct RecipeCard: View {
    let recipe: SeasonalRecipe
    let isFavorite: Bool
    let openRecipe: () -> Void
    let toggleFavorite: () -> Void
    let planRecipe: () -> Void

    var body: some View {
        Button(action: openRecipe) {
            VStack(alignment: .leading, spacing: 12) {
                RecipeImage(url: recipe.thumbnailURL)
                    .frame(height: 120)
                    .clipShape(RoundedRectangle(cornerRadius: 12))

                Text(recipe.name)
                    .font(.headline)
                    .foregroundStyle(SeasonlyColors.ink)
                    .lineLimit(2)
                    .frame(height: 44, alignment: .topLeading)

                Text(recipeSubtitle(recipe))
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)

                SeasonalMatchPill(count: recipe.matchedSeasonalProduceCount)

                HStack {
                    Button(action: toggleFavorite) {
                        Image(systemName: isFavorite ? "heart.fill" : "heart")
                    }
                    .buttonStyle(.bordered)
                    .tint(SeasonlyColors.brown)

                    Button(action: planRecipe) {
                        Image(systemName: "calendar.badge.plus")
                    }
                    .buttonStyle(.bordered)
                    .tint(SeasonlyColors.brown)
                }
            }
            .padding(12)
            .frame(width: 236)
            .background(Color.white.opacity(0.78), in: RoundedRectangle(cornerRadius: 16))
        }
        .buttonStyle(.plain)
    }
}

private struct RecipeListCard: View {
    let recipe: SeasonalRecipe
    let isFavorite: Bool
    let openRecipe: () -> Void
    let toggleFavorite: () -> Void
    let planRecipe: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            RecipeImage(url: recipe.thumbnailURL)
                .frame(width: 88, height: 88)
                .clipShape(RoundedRectangle(cornerRadius: 12))

            VStack(alignment: .leading, spacing: 6) {
                Text(recipe.name)
                    .font(.headline)
                    .foregroundStyle(SeasonlyColors.ink)
                    .lineLimit(2)
                Text(recipeSubtitle(recipe))
                    .font(.caption)
                    .foregroundStyle(.secondary)
                SeasonalMatchPill(count: recipe.matchedSeasonalProduceCount)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            VStack(spacing: 8) {
                Button(action: toggleFavorite) {
                    Image(systemName: isFavorite ? "heart.fill" : "heart")
                }
                Button(action: planRecipe) {
                    Image(systemName: "calendar.badge.plus")
                }
            }
            .buttonStyle(.bordered)
            .tint(SeasonlyColors.brown)
        }
        .contentShape(Rectangle())
        .onTapGesture(perform: openRecipe)
        .padding(12)
        .background(Color.white.opacity(0.78), in: RoundedRectangle(cornerRadius: 16))
    }
}

private struct RecipeDetailView: View {
    let recipe: SeasonalRecipe
    let regionLabel: String
    let isFavorite: Bool
    let toggleFavorite: () -> Void
    let planRecipe: () -> Void

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    RecipeImage(url: recipe.thumbnailURL)
                        .frame(height: 240)
                        .clipShape(RoundedRectangle(cornerRadius: 18))

                    HStack(alignment: .top) {
                        VStack(alignment: .leading, spacing: 8) {
                            Text(recipe.name)
                                .font(.largeTitle.weight(.bold))
                                .foregroundStyle(SeasonlyColors.ink)
                            Text(recipeSubtitle(recipe))
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        Button(action: toggleFavorite) {
                            Image(systemName: isFavorite ? "heart.fill" : "heart")
                                .frame(width: 44, height: 44)
                        }
                        .buttonStyle(.bordered)
                        .tint(SeasonlyColors.brown)
                    }

                    DetailBlock(title: "Seasonal match") {
                        Text("\(recipe.matchedSeasonalProduceCount) ingredients are currently in season in \(regionLabel).")
                        if !recipe.matchedSeasonalProduce.isEmpty {
                            Text(recipe.matchedSeasonalProduce.joined(separator: ", "))
                                .foregroundStyle(.secondary)
                        }
                    }

                    if let instructions = recipe.instructions?.trimmingCharacters(in: .whitespacesAndNewlines),
                       !instructions.isEmpty {
                        DetailBlock(title: "Instructions") {
                            Text(instructions)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }

                    Button {
                        planRecipe()
                    } label: {
                        Label("Add to planner", systemImage: "calendar.badge.plus")
                            .font(.headline)
                            .frame(maxWidth: .infinity)
                            .frame(height: 52)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(SeasonlyColors.brown)
                }
                .padding(18)
            }
            .background(AppBackground())
            .navigationTitle("Recipe")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

private struct ProduceStrip: View {
    let regionLabel: String
    let produce: [SeasonalProduce]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(title: "In season near you", actionTitle: nil, action: {})
            if produce.isEmpty {
                EmptyState(icon: "leaf", title: "No produce loaded", message: "Seasonal produce will appear here once the backend returns data.")
            } else {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 10) {
                        ForEach(produce) { item in
                            VStack(alignment: .leading, spacing: 6) {
                                Text(item.name)
                                    .font(.headline)
                                    .foregroundStyle(SeasonlyColors.ink)
                                Text("In season in \(regionLabel)")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            .padding(14)
                            .frame(width: 166, alignment: .leading)
                            .background(Color.white.opacity(0.74), in: RoundedRectangle(cornerRadius: 14))
                        }
                    }
                }
            }
        }
    }
}

private struct ProduceDetailCard: View {
    let item: SeasonalProduce
    let regionLabel: String

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(item.name.uppercased())
                .font(.headline)
                .foregroundStyle(SeasonlyColors.ink)
            Text("In season in \(regionLabel)")
                .font(.subheadline.weight(.semibold))
            Text("Source: \(item.sourceName)")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white.opacity(0.78), in: RoundedRectangle(cornerRadius: 16))
    }
}

private struct PlannerSheet: View {
    @Environment(\.dismiss) private var dismiss
    let recipe: SeasonalRecipe
    let add: (Weekday, MealSlot) -> Void
    @State private var selectedDay = Weekday.monday
    @State private var selectedMeal = MealSlot.dinner

    var body: some View {
        NavigationStack {
            Form {
                Section("Recipe") {
                    Text(recipe.name)
                }
                Section("Day") {
                    Picker("Day", selection: $selectedDay) {
                        ForEach(Weekday.allCases) { Text($0.rawValue).tag($0) }
                    }
                }
                Section("Meal") {
                    Picker("Meal", selection: $selectedMeal) {
                        ForEach(MealSlot.allCases) { Text($0.rawValue).tag($0) }
                    }
                    .pickerStyle(.segmented)
                }
            }
            .navigationTitle("Add to planner")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Add") {
                        add(selectedDay, selectedMeal)
                        dismiss()
                    }
                }
            }
        }
    }
}

private struct PlannerDayCard: View {
    let day: Weekday
    let meals: [PlannedMeal]
    let remove: (PlannedMeal) -> Void
    let openRecipe: (SeasonalRecipe) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(day.rawValue.uppercased())
                .font(.caption.weight(.bold))
                .foregroundStyle(.secondary)

            if meals.isEmpty {
                Text("Nothing planned")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(meals) { meal in
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(meal.meal.rawValue)
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.secondary)
                            Text(meal.recipe.name)
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(SeasonlyColors.ink)
                        }
                        Spacer()
                        Button { openRecipe(meal.recipe) } label: { Image(systemName: "arrow.up.right") }
                        Button(role: .destructive) { remove(meal) } label: { Image(systemName: "trash") }
                    }
                }
                .buttonStyle(.bordered)
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white.opacity(0.78), in: RoundedRectangle(cornerRadius: 16))
    }
}

private struct WeekPreview: View {
    let plannedMeals: [PlannedMeal]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            ForEach(Weekday.allCases.prefix(3)) { day in
                HStack {
                    Text(day.rawValue)
                        .font(.subheadline.weight(.semibold))
                        .frame(width: 92, alignment: .leading)
                    Text(plannedMeals.first { $0.day == day }?.recipe.name ?? "Nothing planned")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }
        }
        .padding(16)
        .background(Color.white.opacity(0.74), in: RoundedRectangle(cornerRadius: 16))
    }
}

private struct WeekPlannerHeader: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("My week")
                .font(.title2.weight(.bold))
                .foregroundStyle(SeasonlyColors.ink)
            Text("Add recipes from Home, Explore or Saved. Shopping lists and auto-planning can come later.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }
}

private struct ProfileSettingsView: View {
    @Bindable var session: AuthenticationSession
    let user: SeasonlyUser
    let profile: OnboardingProfile?
    let logout: () -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var countries: [CountryReference] = []
    @State private var cuisines: [CuisineReference] = []
    @State private var allergens: [EnumReference] = []
    @State private var proteins: [EnumReference] = []
    @State private var locationDetector = LocationDetector()
    @State private var selectedCountryCode = ""
    @State private var selectedRegionCode = ""
    @State private var selectedLocationSource = "manual"
    @State private var selectedDiet = ""
    @State private var allergyStatus = "not_provided"
    @State private var selectedAllergens = Set<String>()
    @State private var allergyConsent = false
    @State private var selectedDietaryRules = Set<String>()
    @State private var selectedCuisines: [String] = []
    @State private var selectedProteins: [String] = []
    @State private var saveMessage: String?
    @State private var isSaving = false

    var body: some View {
        NavigationStack {
            List {
                Section("Account") {
                    LabeledContent("Email", value: user.email)
                    Button("Sign out", role: .destructive, action: logout)
                }
                Section("Location") {
                    Button {
                        detectCurrentLocation()
                    } label: {
                        Label(
                            locationDetector.isDetecting ? "Detecting location..." : "Use current location",
                            systemImage: "location.fill"
                        )
                    }
                    .disabled(locationDetector.isDetecting)

                    Picker("Country", selection: countrySelection) {
                        Text("Select country").tag("")
                        ForEach(countries) { country in
                            Text(country.name).tag(country.code)
                        }
                    }
                    TextField("Region code (optional)", text: regionSelection)
                        .textInputAutocapitalization(.characters)
                        .autocorrectionDisabled()
                    if let message = locationDetector.message {
                        Text(message)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    Text("Seasonly uses coarse location only. Continuous tracking is not required.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Section("Dietary profile") {
                    Picker("Diet", selection: $selectedDiet) {
                        ForEach(profileDietOptions, id: \.value) { option in
                            Text(option.label).tag(option.value)
                        }
                    }
                }
                Section("Allergies") {
                    Picker("Allergy answer", selection: $allergyStatus) {
                        Text("No known allergies").tag("no_known_allergies")
                        Text("Yes, I have allergies").tag("provided")
                        Text("Prefer not to say").tag("not_provided")
                    }
                    if allergyStatus == "provided" {
                        MultiSelectRows(options: allergens, selection: $selectedAllergens)
                        Toggle("I consent to storing and using allergy information", isOn: $allergyConsent)
                    }
                }
                Section("Foods avoided") {
                    MultiSelectRows(options: dietaryRuleReferences, selection: $selectedDietaryRules)
                }
                Section("Favourite cuisines") {
                    Button {
                        selectedCuisines.removeAll()
                    } label: {
                        HStack {
                            Text("No preference")
                                .foregroundStyle(SeasonlyColors.ink)
                            Spacer()
                            if selectedCuisines.isEmpty {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundStyle(SeasonlyColors.brown)
                            }
                        }
                    }
                    MultiSelectRows(
                        options: cuisines.map { EnumReference(value: $0.area, label: $0.area) },
                        selection: Binding(
                            get: { Set(selectedCuisines) },
                            set: { selectedCuisines = Array($0).sorted() }
                        ),
                        limit: 5
                    )
                    Text("Choose up to five, or leave No preference selected.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Section("Favourite proteins") {
                    MultiSelectRows(
                        options: compatibleProteinReferences,
                        selection: Binding(
                            get: { Set(selectedProteins) },
                            set: { selectedProteins = Array($0).sorted() }
                        ),
                        limit: 5
                    )
                    Text("Protein options are filtered by diet, allergies and avoided foods.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Section("Data and privacy") {
                    Text("Use these controls to correct the profile data used for filtering and recommendations. Data export, history clearing and account deletion still need dedicated backend endpoints before shipping.")
                        .font(.subheadline)
                }
                Section("About") {
                    Text("Recipe and seasonal data attribution will use backend source metadata where available.")
                        .font(.subheadline)
                    Text("Recommendations are guidance only and are not medical advice.")
                        .font(.subheadline)
                }
                if let saveMessage {
                    Section {
                        Text(saveMessage)
                            .font(.subheadline)
                            .foregroundStyle(saveMessage == "Saved" ? .green : .red)
                    }
                }
            }
            .navigationTitle("Profile")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                        .disabled(isSaving)
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await saveAndDismiss() }
                    } label: {
                        if isSaving {
                            ProgressView()
                        } else {
                            Text("Done")
                        }
                    }
                    .disabled(!canSaveProfile || isSaving || session.isLoading)
                }
            }
            .task {
                hydrate()
                await loadReferences()
            }
        }
    }

    private var canSaveAllergies: Bool {
        allergyStatus != "provided" || (!selectedAllergens.isEmpty && allergyConsent)
    }

    private var canSaveProfile: Bool {
        !selectedCountryCode.isEmpty && !selectedDiet.isEmpty && canSaveAllergies
    }

    private var countrySelection: Binding<String> {
        Binding(
            get: { selectedCountryCode },
            set: {
                selectedCountryCode = $0
                selectedLocationSource = "manual"
            }
        )
    }

    private var regionSelection: Binding<String> {
        Binding(
            get: { selectedRegionCode },
            set: {
                selectedRegionCode = $0
                selectedLocationSource = "manual"
            }
        )
    }

    private var compatibleProteinReferences: [EnumReference] {
        let allowed: Set<String>
        switch selectedDiet {
        case "pescatarian":
            allowed = ["fish", "seafood", "eggs", "tofu", "legumes"]
        case "vegetarian":
            allowed = ["eggs", "tofu", "legumes"]
        case "vegan":
            allowed = ["tofu", "legumes"]
        default:
            allowed = ["chicken", "turkey", "beef", "pork", "lamb", "fish", "seafood", "eggs", "tofu", "legumes"]
        }
        return proteins.filter { allowed.contains($0.value) && !blockedProteins.contains($0.value) }
    }

    private var blockedProteins: Set<String> {
        var blocked = Set<String>()
        if selectedDietaryRules.contains("avoid_pork") { blocked.insert("pork") }
        if selectedDietaryRules.contains("avoid_beef") { blocked.insert("beef") }
        if selectedDietaryRules.contains("avoid_shellfish") { blocked.insert("seafood") }
        if selectedAllergens.contains("fish") { blocked.insert("fish") }
        if selectedAllergens.contains("crustaceans") { blocked.insert("seafood") }
        if selectedAllergens.contains("molluscs") { blocked.insert("seafood") }
        if selectedAllergens.contains("eggs") { blocked.insert("eggs") }
        return blocked
    }

    private func hydrate() {
        let currentProfile = session.onboardingProfile ?? profile
        selectedCountryCode = currentProfile?.countryCode ?? user.profile?.countryCode ?? ""
        selectedRegionCode = currentProfile?.regionCode ?? user.profile?.regionCode ?? ""
        selectedLocationSource = currentProfile?.locationSource ?? user.profile?.locationSource ?? "manual"
        selectedDiet = currentProfile?.dietPattern ?? "omnivore"
        allergyStatus = currentProfile?.allergyStatus ?? "not_provided"
        selectedAllergens = Set(currentProfile?.allergens ?? [])
        allergyConsent = !(currentProfile?.allergens.isEmpty ?? true)
        selectedDietaryRules = Set(currentProfile?.dietaryRules ?? [])
        selectedCuisines = currentProfile?.cuisineAreas ?? []
        selectedProteins = currentProfile?.proteins ?? []
    }

    private func loadReferences() async {
        guard let references = await session.fetchOnboardingReferences() else { return }
        countries = references.0
        cuisines = references.1
        allergens = references.2
        proteins = references.3
    }

    private func saveAndDismiss() async {
        guard canSaveProfile else { return }
        isSaving = true
        saveMessage = nil
        pruneProteins()
        defer { isSaving = false }

        let finalProteins = selectedProteins
        let region = selectedRegionCode.trimmingCharacters(in: .whitespacesAndNewlines)
        let locationSaved = await session.updateLocation(
            countryCode: selectedCountryCode,
            regionCode: region.isEmpty ? nil : region.uppercased(),
            source: selectedLocationSource
        )
        guard locationSaved else {
            saveMessage = session.errorMessage ?? "Location save failed"
            return
        }

        guard await session.updateProteins([]) else {
            saveMessage = session.errorMessage ?? "Protein save failed"
            return
        }

        guard await session.updateDiet(selectedDiet) else {
            saveMessage = session.errorMessage ?? "Diet save failed"
            return
        }

        if allergyStatus != "provided" {
            selectedAllergens.removeAll()
            allergyConsent = false
        }
        guard await session.updateAllergies(
            status: allergyStatus,
            allergens: Array(selectedAllergens).sorted(),
            explicitConsent: allergyStatus == "provided" && allergyConsent
        ) else {
            saveMessage = session.errorMessage ?? "Allergy save failed"
            return
        }

        guard await session.updateDietaryRules(Array(selectedDietaryRules).sorted()) else {
            saveMessage = session.errorMessage ?? "Avoided foods save failed"
            return
        }

        let cuisineStatus = selectedCuisines.isEmpty ? "no_preference" : "provided"
        guard await session.updateCuisines(status: cuisineStatus, areas: selectedCuisines) else {
            saveMessage = session.errorMessage ?? "Cuisine save failed"
            return
        }

        guard await session.updateProteins(finalProteins) else {
            saveMessage = session.errorMessage ?? "Protein save failed"
            return
        }

        dismiss()
    }

    private func pruneProteins() {
        let allowed = Set(compatibleProteinReferences.map(\.value))
        selectedProteins.removeAll { !allowed.contains($0) }
    }

    private func detectCurrentLocation() {
        locationDetector.detect { countryCode, regionCode in
            let normalizedCountryCode = normalizeDetectedCountryCode(countryCode)
            guard countries.isEmpty || countries.contains(where: { $0.code == normalizedCountryCode }) else {
                if let localeCountry = supportedLocaleCountryCode() {
                    selectedCountryCode = localeCountry
                    selectedRegionCode = ""
                    selectedLocationSource = "device"
                    locationDetector.stopDetecting(
                        message: "Detected \(countryCode), but it is not supported. Using your device region instead; please confirm before tapping Done."
                    )
                    return
                }

                locationDetector.stopDetecting(
                    message: "Detected \(countryCode), but it is not currently supported. Choose the country manually instead."
                )
                return
            }

            selectedCountryCode = normalizedCountryCode
            selectedRegionCode = regionCode ?? ""
            selectedLocationSource = "device"
            locationDetector.stopDetecting(message: "Detected location. Please confirm before tapping Done.")
        } onFallback: {
            if selectedCountryCode.isEmpty, let localeCountry = supportedLocaleCountryCode() {
                selectedCountryCode = localeCountry
                selectedLocationSource = "manual"
            }
        }
    }

    private func supportedLocaleCountryCode() -> String? {
        guard let localeIdentifier = Locale.current.region?.identifier else { return nil }
        let localeCountry = normalizeDetectedCountryCode(localeIdentifier)
        return countries.contains(where: { $0.code == localeCountry }) ? localeCountry : nil
    }

    private func normalizeDetectedCountryCode(_ value: String) -> String {
        switch value.trimmingCharacters(in: .whitespacesAndNewlines).uppercased() {
        case "UK", "ENG", "ENGLAND", "SCOTLAND", "SCT", "WALES", "WLS", "NORTHERN IRELAND", "NIR":
            return "GB"
        default:
            return value.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        }
    }
}

private let profileDietOptions: [EnumReference] = [
    EnumReference(value: "omnivore", label: "Omnivore"),
    EnumReference(value: "flexitarian", label: "Flexitarian"),
    EnumReference(value: "pescatarian", label: "Pescatarian"),
    EnumReference(value: "vegetarian", label: "Vegetarian"),
    EnumReference(value: "vegan", label: "Vegan")
]

private let dietaryRuleReferences: [EnumReference] = [
    EnumReference(value: "avoid_pork", label: "Pork"),
    EnumReference(value: "avoid_beef", label: "Beef"),
    EnumReference(value: "avoid_alcohol", label: "Alcohol"),
    EnumReference(value: "avoid_shellfish", label: "Shellfish")
]

private struct MultiSelectRows: View {
    let options: [EnumReference]
    @Binding var selection: Set<String>
    var limit: Int?

    var body: some View {
        ForEach(options) { option in
            Button {
                toggle(option.value)
            } label: {
                HStack {
                    Text(option.label)
                        .foregroundStyle(SeasonlyColors.ink)
                    Spacer()
                    if selection.contains(option.value) {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundStyle(SeasonlyColors.brown)
                    }
                }
            }
            .disabled(isDisabled(option.value))
        }
    }

    private func toggle(_ value: String) {
        if selection.contains(value) {
            selection.remove(value)
        } else if limit == nil || selection.count < (limit ?? 0) {
            selection.insert(value)
        }
    }

    private func isDisabled(_ value: String) -> Bool {
        guard let limit else { return false }
        return !selection.contains(value) && selection.count >= limit
    }
}

private struct SectionHeader: View {
    let title: String
    let actionTitle: String?
    let action: () -> Void

    var body: some View {
        HStack {
            Text(title)
                .font(.title3.weight(.bold))
                .foregroundStyle(SeasonlyColors.ink)
            Spacer()
            if let actionTitle {
                Button(actionTitle, action: action)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(SeasonlyColors.brown)
            }
        }
    }
}

private struct SeasonalMatchPill: View {
    let count: Int

    var body: some View {
        Label("\(count) seasonal", systemImage: "leaf.fill")
            .font(.caption.weight(.semibold))
            .foregroundStyle(Color(red: 0.12, green: 0.42, blue: 0.22))
            .padding(.horizontal, 9)
            .padding(.vertical, 6)
            .background(Color(red: 0.84, green: 0.93, blue: 0.78), in: Capsule())
    }
}

private struct LocationPill: View {
    let regionLabel: String

    var body: some View {
        Label(regionLabel, systemImage: "location.fill")
            .font(.caption.weight(.semibold))
            .foregroundStyle(SeasonlyColors.ink)
            .padding(.horizontal, 10)
            .padding(.vertical, 7)
            .background(Color.white.opacity(0.78), in: Capsule())
    }
}

private struct RecipeImage: View {
    let url: URL?

    var body: some View {
        ZStack {
            Rectangle()
                .fill(Color(red: 0.83, green: 0.88, blue: 0.73))
            if let url {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let image):
                        image.resizable().scaledToFill()
                    case .failure:
                        Image(systemName: "fork.knife")
                            .font(.title)
                            .foregroundStyle(SeasonlyColors.brown)
                    case .empty:
                        ProgressView().tint(SeasonlyColors.brown)
                    @unknown default:
                        EmptyView()
                    }
                }
            } else {
                Image(systemName: "fork.knife")
                    .font(.title)
                    .foregroundStyle(SeasonlyColors.brown)
            }
        }
        .clipped()
    }
}

private struct DetailBlock<Content: View>: View {
    let title: String
    @ViewBuilder let content: Content

    init(title: String, @ViewBuilder content: () -> Content) {
        self.title = title
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title)
                .font(.headline)
                .foregroundStyle(SeasonlyColors.ink)
            content
                .font(.subheadline)
                .foregroundStyle(SeasonlyColors.ink)
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white.opacity(0.76), in: RoundedRectangle(cornerRadius: 16))
    }
}

private struct EmptyState: View {
    let icon: String
    let title: String
    let message: String

    var body: some View {
        VStack(spacing: 10) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundStyle(SeasonlyColors.brown)
            Text(title)
                .font(.headline)
                .foregroundStyle(SeasonlyColors.ink)
            Text(message)
                .font(.subheadline)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(24)
        .background(Color.white.opacity(0.72), in: RoundedRectangle(cornerRadius: 16))
    }
}

private struct AppBackground: View {
    var body: some View {
        LinearGradient(
            colors: [
                Color(red: 0.95, green: 0.91, blue: 0.82),
                Color(red: 0.84, green: 0.9, blue: 0.78),
                Color(red: 0.72, green: 0.82, blue: 0.76)
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
        .ignoresSafeArea()
    }
}

private func recipeSubtitle(_ recipe: SeasonalRecipe) -> String {
    [recipe.area, recipe.category].compactMap { $0 }.joined(separator: " • ")
}

#Preview {
    MainAppView(session: AuthenticationSession(), user: SeasonlyUser(
        id: UUID(),
        email: "fabio@example.com",
        isActive: true,
        isVerified: false,
        createdAt: Date(),
        updatedAt: Date(),
        profile: nil
    )) {}
}
