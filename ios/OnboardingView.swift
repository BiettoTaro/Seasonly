import CoreLocation
import MapKit
import SwiftUI

struct OnboardingView: View {
    @Bindable var session: AuthenticationSession
    @State private var locationDetector = LocationDetector()
    @State private var countries: [CountryReference] = []
    @State private var cuisines: [CuisineReference] = []
    @State private var allergenOptions: [EnumReference] = []
    @State private var proteinOptions: [EnumReference] = []
    @State private var currentPage: OnboardingPage = .privacy
    @State private var locationMethod: LocationMethod?
    @State private var selectedCountryCode: String?
    @State private var selectedRegionCode: String?
    @State private var locationSource = "manual"
    @State private var selectedDiet: String?
    @State private var allergyAnswer: AllergyAnswer?
    @State private var selectedAllergens = Set<String>()
    @State private var allergyConsent = false
    @State private var selectedDietaryRules = Set<String>()
    @State private var noCuisinePreference = false
    @State private var selectedCuisines: [String] = []
    @State private var selectedProteins: [String] = []
    @State private var noticeMessage: String?
    @State private var hasLoadedReferences = false

    private var visiblePages: [OnboardingPage] {
        var pages: [OnboardingPage] = [
            .privacy,
            .locationMethod,
            .confirmLocation,
            .diet,
            .allergyQuestion
        ]
        if allergyAnswer == .provided {
            pages.append(.allergens)
        }
        pages.append(contentsOf: [.dietaryRules, .cuisines])
        if requiresProteinPage {
            pages.append(.proteins)
        }
        pages.append(.review)
        return pages
    }

    private var progress: Double {
        guard let index = visiblePages.firstIndex(of: currentPage) else { return 0.05 }
        return Double(index + 1) / Double(visiblePages.count)
    }

    private var requiresProteinPage: Bool {
        guard let selectedDiet else { return false }
        return ["omnivore", "flexitarian", "pescatarian"].contains(selectedDiet)
    }

    private var canContinue: Bool {
        switch currentPage {
        case .privacy:
            return true
        case .locationMethod:
            return locationMethod != nil && !locationDetector.isDetecting
        case .confirmLocation:
            return selectedCountryCode != nil
        case .diet:
            return selectedDiet != nil
        case .allergyQuestion:
            return allergyAnswer != nil
        case .allergens:
            return !selectedAllergens.isEmpty && allergyConsent
        case .dietaryRules:
            return true
        case .cuisines:
            return noCuisinePreference || !selectedCuisines.isEmpty
        case .proteins:
            return !selectedProteins.isEmpty
        case .review:
            return true
        }
    }

    var body: some View {
        ZStack {
            RusticBackground()

            VStack(spacing: 0) {
                header

                ScrollView {
                    VStack(alignment: .leading, spacing: 22) {
                        if let noticeMessage {
                            StatusMessage(message: noticeMessage, isError: false)
                        }

                        if let errorMessage = session.errorMessage {
                            StatusMessage(message: errorMessage, isError: true)
                        }

                        pageContent
                    }
                    .padding(22)
                    .frame(maxWidth: 620, alignment: .leading)
                    .frame(maxWidth: .infinity)
                }

                footer
            }
        }
        .task {
            await loadReferencesIfNeeded()
            hydrateFromProfile()
        }
        .onChange(of: session.onboardingProfile?.updatedAt) {
            hydrateFromProfile()
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 12) {
                Image(systemName: iconName)
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(Color.white)
                    .frame(width: 40, height: 40)
                    .background(SeasonlyColors.brown, in: RoundedRectangle(cornerRadius: 10))

                VStack(alignment: .leading, spacing: 2) {
                    Text("Set up Seasonly")
                        .font(.headline)
                        .foregroundStyle(SeasonlyColors.ink)
                    Text(currentPage.title)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                Button {
                    Task { await session.logout() }
                } label: {
                    Image(systemName: "rectangle.portrait.and.arrow.right")
                        .frame(width: 38, height: 38)
                }
                .buttonStyle(.bordered)
                .tint(SeasonlyColors.brown)
                .accessibilityLabel("Sign out")
            }

            ProgressView(value: progress)
                .tint(SeasonlyColors.brown)
        }
        .padding(.horizontal, 22)
        .padding(.top, 18)
        .padding(.bottom, 12)
        .background(.regularMaterial)
    }

    @ViewBuilder
    private var pageContent: some View {
        switch currentPage {
        case .privacy:
            PrivacyPage()
        case .locationMethod:
            LocationMethodPage(
                selection: $locationMethod,
                detector: locationDetector,
                detectLocation: detectLocation,
                chooseManually: { chooseLocationManually() }
            )
        case .confirmLocation:
            ConfirmLocationPage(
                countries: countries,
                selectedCountryCode: $selectedCountryCode,
                selectedRegionCode: $selectedRegionCode,
                locationMethod: locationMethod,
                detectorMessage: locationDetector.message
            )
        case .diet:
            SingleChoicePage(
                title: "How do you usually eat?",
                subtitle: "Choose one. This keeps recipe filtering consistent.",
                options: DietOption.all,
                selection: Binding(
                    get: { selectedDiet },
                    set: { updateDietSelection($0) }
                )
            )
        case .allergyQuestion:
            AllergyQuestionPage(selection: $allergyAnswer)
        case .allergens:
            AllergensPage(
                options: allergenOptions,
                selection: $selectedAllergens,
                consent: $allergyConsent
            )
        case .dietaryRules:
            DietaryRulesPage(selection: $selectedDietaryRules)
        case .cuisines:
            CuisinesPage(
                cuisines: cuisines,
                selectedCuisines: $selectedCuisines,
                noPreference: $noCuisinePreference
            )
        case .proteins:
            ProteinsPage(
                options: compatibleProteins,
                selectedProteins: $selectedProteins
            )
        case .review:
            ReviewPage(
                countryName: countryName(for: selectedCountryCode),
                regionCode: selectedRegionCode,
                diet: DietOption.label(for: selectedDiet),
                allergyAnswer: allergyAnswer?.title,
                allergens: labels(for: selectedAllergens, in: allergenOptions),
                dietaryRules: DietaryRuleOption.labels(for: selectedDietaryRules),
                cuisines: noCuisinePreference ? ["No preference"] : selectedCuisines,
                proteins: labels(for: Set(selectedProteins), in: proteinOptions),
                edit: { currentPage = $0 }
            )
        }
    }

    private var footer: some View {
        HStack(spacing: 12) {
            Button("Back") {
                goBack()
            }
            .buttonStyle(.bordered)
            .tint(SeasonlyColors.brown)
            .disabled(currentPage == visiblePages.first || session.isLoading)

            Button {
                Task { await continueTapped() }
            } label: {
                Group {
                    if session.isLoading {
                        ProgressView().tint(.white)
                    } else {
                        Text(currentPage == .review ? "Finish" : "Continue")
                    }
                }
                .font(.headline)
                .frame(maxWidth: .infinity)
                .frame(height: 48)
            }
            .buttonStyle(.borderedProminent)
            .tint(canContinue ? SeasonlyColors.brown : .gray)
            .disabled(!canContinue || session.isLoading)
        }
        .padding(22)
        .background(.regularMaterial)
    }

    private var iconName: String {
        switch currentPage {
        case .privacy: "lock.shield"
        case .locationMethod, .confirmLocation: "location"
        case .diet, .dietaryRules, .cuisines, .proteins: "fork.knife"
        case .allergyQuestion, .allergens: "allergens"
        case .review: "checkmark.seal"
        }
    }

    private var compatibleProteins: [EnumReference] {
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

        let blocked = blockedProteins
        let filtered = proteinOptions.filter { allowed.contains($0.value) && !blocked.contains($0.value) }
        if selectedDiet == "flexitarian" {
            let plantFirst = ["tofu", "legumes", "eggs", "fish", "seafood", "chicken", "turkey", "beef", "pork", "lamb"]
            return filtered.sorted { left, right in
                (plantFirst.firstIndex(of: left.value) ?? 99) < (plantFirst.firstIndex(of: right.value) ?? 99)
            }
        }
        return filtered
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

    private func continueTapped() async {
        noticeMessage = nil
        session.errorMessage = nil

        let succeeded: Bool
        switch currentPage {
        case .privacy:
            succeeded = await session.acknowledgePrivacy()
        case .locationMethod:
            succeeded = true
        case .confirmLocation:
            guard let selectedCountryCode else { return }
            succeeded = await session.updateLocation(
                countryCode: selectedCountryCode,
                regionCode: selectedRegionCode?.isEmpty == true ? nil : selectedRegionCode,
                source: locationSource
            )
        case .diet:
            guard let selectedDiet else { return }
            await clearBackendProteinsIfNeeded(for: selectedDiet)
            succeeded = await session.updateDiet(selectedDiet)
        case .allergyQuestion:
            guard let allergyAnswer else { return }
            if allergyAnswer == .provided {
                succeeded = true
            } else {
                selectedAllergens.removeAll()
                allergyConsent = false
                succeeded = await session.updateAllergies(
                    status: allergyAnswer.backendValue,
                    allergens: [],
                    explicitConsent: false
                )
            }
        case .allergens:
            await clearBackendProteinsIfNeeded(for: selectedDiet)
            succeeded = await session.updateAllergies(
                status: "provided",
                allergens: Array(selectedAllergens).sorted(),
                explicitConsent: allergyConsent
            )
        case .dietaryRules:
            await clearBackendProteinsIfNeeded(for: selectedDiet)
            succeeded = await session.updateDietaryRules(Array(selectedDietaryRules).sorted())
        case .cuisines:
            let status = noCuisinePreference ? "no_preference" : "provided"
            succeeded = await session.updateCuisines(status: status, areas: noCuisinePreference ? [] : selectedCuisines)
        case .proteins:
            succeeded = await session.updateProteins(selectedProteins)
        case .review:
            succeeded = await session.completeOnboarding()
        }

        guard succeeded else { return }
        goForward()
    }

    private func goForward() {
        guard currentPage != .review else { return }
        let pages = visiblePages
        guard let index = pages.firstIndex(of: currentPage), index + 1 < pages.count else { return }
        currentPage = pages[index + 1]
    }

    private func goBack() {
        let pages = visiblePages
        guard let index = pages.firstIndex(of: currentPage), index > 0 else { return }
        currentPage = pages[index - 1]
    }

    private func detectLocation() {
        locationMethod = .device
        locationSource = "device"
        locationDetector.detect { countryCode, regionCode in
            let normalizedCountryCode = normalizeDetectedCountryCode(countryCode)
            guard countries.isEmpty || countryHasSeasonalData(normalizedCountryCode) else {
                let supportedCodes = countries.map(\.code).joined(separator: ", ")
                if let localeCountry = supportedLocaleCountryCode() {
                    locationDetector.stopDetecting(
                        message: "Simulator/device location returned '\(countryCode)'. Using your device region '\(localeCountry)' instead; please confirm it."
                    )
                    print("Seasonly location debug: raw=\(countryCode), normalized=\(normalizedCountryCode), localeFallback=\(localeCountry), region=\(regionCode ?? "nil"), supported=\(supportedCodes)")
                    selectedCountryCode = localeCountry
                    selectedRegionCode = nil
                    currentPage = .confirmLocation
                    return
                }
                locationDetector.stopDetecting(
                    message: "Detected country '\(countryCode)' normalized to '\(normalizedCountryCode)', but supported countries are: \(supportedCodes)."
                )
                print("Seasonly location debug: raw=\(countryCode), normalized=\(normalizedCountryCode), region=\(regionCode ?? "nil"), supported=\(supportedCodes)")
                chooseLocationManually()
                return
            }
            print("Seasonly location debug: accepted raw=\(countryCode), normalized=\(normalizedCountryCode), region=\(regionCode ?? "nil")")
            selectedCountryCode = normalizedCountryCode
            selectedRegionCode = regionCode
            currentPage = .confirmLocation
        } onFallback: {
            chooseLocationManually(prefillFromLocale: true)
        }
    }

    private func chooseLocationManually(prefillFromLocale: Bool = false) {
        locationMethod = .manual
        locationSource = "manual"
        locationDetector.stopDetecting(message: locationDetector.message)
        if prefillFromLocale,
           selectedCountryCode == nil,
           let localeIdentifier = Locale.current.region?.identifier,
           let localeCountry = Optional(normalizeDetectedCountryCode(localeIdentifier)),
           countryHasSeasonalData(localeCountry) {
            selectedCountryCode = localeCountry
        }
        currentPage = .confirmLocation
    }

    private func supportedLocaleCountryCode() -> String? {
        guard let localeIdentifier = Locale.current.region?.identifier else { return nil }
        let localeCountry = normalizeDetectedCountryCode(localeIdentifier)
        return countryHasSeasonalData(localeCountry) ? localeCountry : nil
    }

    private func countryHasSeasonalData(_ countryCode: String) -> Bool {
        countries.contains {
            $0.code == countryCode && $0.seasonalDataAvailable
        }
    }

    private func normalizeDetectedCountryCode(_ value: String) -> String {
        switch value.trimmingCharacters(in: .whitespacesAndNewlines).uppercased() {
        case "UK", "ENG", "ENGLAND", "SCOTLAND", "SCT", "WALES", "WLS", "NORTHERN IRELAND", "NIR":
            return "GB"
        default:
            return value.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        }
    }

    private func updateDietSelection(_ newValue: String?) {
        selectedDiet = newValue
        pruneSelectedProteins()
    }

    private func pruneSelectedProteins() {
        let allowed = Set(compatibleProteins.map(\.value))
        let previous = selectedProteins
        selectedProteins.removeAll { !allowed.contains($0) }
        if previous.count != selectedProteins.count {
            noticeMessage = "Incompatible protein preferences were cleared."
        }
    }

    private func clearBackendProteinsIfNeeded(for diet: String?) async {
        guard let profile = session.onboardingProfile, !profile.proteins.isEmpty else { return }
        let allowed = Set(compatibleProteins.map(\.value))
        let retained = profile.proteins.filter { allowed.contains($0) }
        if retained.count != profile.proteins.count {
            _ = await session.updateProteins(retained)
            noticeMessage = "Incompatible protein preferences were cleared."
        }
    }

    private func loadReferencesIfNeeded() async {
        guard !hasLoadedReferences else { return }
        if let references = await session.fetchOnboardingReferences() {
            countries = references.0
            cuisines = references.1
            allergenOptions = references.2
            proteinOptions = references.3
            hasLoadedReferences = true
        }
    }

    private func hydrateFromProfile() {
        guard let profile = session.onboardingProfile else { return }
        selectedCountryCode = selectedCountryCode ?? profile.countryCode
        selectedRegionCode = selectedRegionCode ?? profile.regionCode
        locationSource = profile.locationSource ?? locationSource
        if locationMethod == nil, profile.countryCode != nil {
            locationMethod = profile.locationSource == "device" ? .device : .manual
        }
        selectedDiet = selectedDiet ?? profile.dietPattern
        selectedAllergens = selectedAllergens.isEmpty ? Set(profile.allergens) : selectedAllergens
        selectedDietaryRules = selectedDietaryRules.isEmpty ? Set(profile.dietaryRules) : selectedDietaryRules
        selectedCuisines = selectedCuisines.isEmpty ? profile.cuisineAreas : selectedCuisines
        selectedProteins = selectedProteins.isEmpty ? profile.proteins : selectedProteins
        noCuisinePreference = profile.cuisinePreferenceStatus == "no_preference" || noCuisinePreference
        allergyConsent = !profile.allergens.isEmpty || allergyConsent
        if allergyAnswer == nil {
            allergyAnswer = AllergyAnswer(backendValue: profile.allergyStatus)
        }
        if let backendPage = OnboardingPage(backendStep: profile.nextStep), currentPage == .privacy {
            currentPage = backendPage
        }
        pruneSelectedProteins()
    }

    private func countryName(for code: String?) -> String {
        guard let code else { return "Not selected" }
        return countries.first { $0.code == code }?.name ?? code
    }

    private func labels(for values: Set<String>, in options: [EnumReference]) -> [String] {
        values.sorted().map { value in
            options.first { $0.value == value }?.label ?? value.replacingOccurrences(of: "_", with: " ").capitalized
        }
    }
}

private enum OnboardingPage: Hashable {
    case privacy
    case locationMethod
    case confirmLocation
    case diet
    case allergyQuestion
    case allergens
    case dietaryRules
    case cuisines
    case proteins
    case review

    init?(backendStep: String) {
        switch backendStep {
        case "privacy": self = .privacy
        case "location": self = .locationMethod
        case "diet": self = .diet
        case "allergies": self = .allergyQuestion
        case "dietary_rules": self = .dietaryRules
        case "cuisines": self = .cuisines
        case "proteins": self = .proteins
        case "review": self = .review
        default: return nil
        }
    }

    var title: String {
        switch self {
        case .privacy: "Privacy and data use"
        case .locationMethod: "Location method"
        case .confirmLocation: "Confirm location"
        case .diet: "Diet type"
        case .allergyQuestion: "Food allergies"
        case .allergens: "Allergens"
        case .dietaryRules: "Foods avoided"
        case .cuisines: "Favourite cuisines"
        case .proteins: "Favourite proteins"
        case .review: "Review"
        }
    }
}

private enum LocationMethod: String {
    case device
    case manual
}

private enum AllergyAnswer: String, Identifiable {
    case none
    case provided
    case preferNotToSay

    init?(backendValue: String) {
        switch backendValue {
        case "no_known_allergies": self = .none
        case "provided": self = .provided
        case "not_provided": self = .preferNotToSay
        default: return nil
        }
    }

    var id: String { rawValue }

    var title: String {
        switch self {
        case .none: "No known food allergies"
        case .provided: "Yes, I have food allergies"
        case .preferNotToSay: "Prefer not to say"
        }
    }

    var backendValue: String {
        switch self {
        case .none: "no_known_allergies"
        case .provided: "provided"
        case .preferNotToSay: "not_provided"
        }
    }
}

private enum DietOption {
    static let all = [
        ChoiceOption(value: "omnivore", label: "Omnivore", detail: "Includes meat, fish, dairy and plants."),
        ChoiceOption(value: "flexitarian", label: "Flexitarian", detail: "Mostly plant-led, sometimes meat or fish."),
        ChoiceOption(value: "pescatarian", label: "Pescatarian", detail: "Fish and seafood, no meat."),
        ChoiceOption(value: "vegetarian", label: "Vegetarian", detail: "No meat or fish."),
        ChoiceOption(value: "vegan", label: "Vegan", detail: "Plant-based only.")
    ]

    static func label(for value: String?) -> String {
        guard let value else { return "Not selected" }
        return all.first { $0.value == value }?.label ?? value.capitalized
    }
}

private enum DietaryRuleOption {
    static let all = [
        ChoiceOption(value: "avoid_pork", label: "Pork", detail: nil),
        ChoiceOption(value: "avoid_beef", label: "Beef", detail: nil),
        ChoiceOption(value: "avoid_alcohol", label: "Alcohol", detail: nil),
        ChoiceOption(value: "avoid_shellfish", label: "Shellfish", detail: nil)
    ]

    static func labels(for values: Set<String>) -> [String] {
        guard !values.isEmpty else { return ["None of these"] }
        return values.sorted().map { value in
            all.first { $0.value == value }?.label ?? value
        }
    }
}

private struct ChoiceOption: Identifiable, Hashable {
    let value: String
    let label: String
    let detail: String?

    var id: String { value }
}

private struct PrivacyPage: View {
    var body: some View {
        PageIntro(
            title: "Privacy and data use",
            subtitle: "Seasonly uses only the information needed to filter recipes and recommend seasonal food."
        )

        VStack(alignment: .leading, spacing: 14) {
            InfoRow(icon: "location", text: "We store your country and, where useful, a coarse region. Exact coordinates are not stored.")
            InfoRow(icon: "fork.knife", text: "Diet type, allergies, avoided foods and preferences are used for recipe filtering and recommendations.")
            InfoRow(icon: "lock.shield", text: "Allergy details are stored only if you choose Yes and give explicit consent.")
        }

        Link("Full privacy notice", destination: URL(string: "https://seasonly.app/privacy")!)
            .font(.subheadline.weight(.semibold))
            .foregroundStyle(SeasonlyColors.brown)
    }
}

private struct LocationMethodPage: View {
    @Binding var selection: LocationMethod?
    let detector: LocationDetector
    let detectLocation: () -> Void
    let chooseManually: () -> Void

    var body: some View {
        PageIntro(
            title: "How should we set your location?",
            subtitle: "Seasonly uses location to choose the right seasonal produce data."
        )

        VStack(spacing: 12) {
            Button {
                detectLocation()
            } label: {
                MethodRow(
                    icon: "location.fill",
                    title: "Use my current location",
                    detail: "iOS permission is requested only after this tap.",
                    isSelected: selection == .device
                )
            }
            .buttonStyle(.plain)

            Button {
                chooseManually()
            } label: {
                MethodRow(
                    icon: "globe.europe.africa.fill",
                    title: "Choose country manually",
                    detail: "No location permission needed.",
                    isSelected: selection == .manual
                )
            }
            .buttonStyle(.plain)
        }

        if detector.isDetecting {
            HStack(spacing: 10) {
                ProgressView()
                Text("Detecting country...")
            }
            .font(.subheadline)
            .foregroundStyle(.secondary)
        }
    }
}

private struct ConfirmLocationPage: View {
    let countries: [CountryReference]
    @Binding var selectedCountryCode: String?
    @Binding var selectedRegionCode: String?
    let locationMethod: LocationMethod?
    let detectorMessage: String?

    var body: some View {
        PageIntro(
            title: "Confirm your seasonal region",
            subtitle: "Country is required. Current seasonal data is country-level, so no region selector is shown yet."
        )

        if let detectorMessage {
            StatusMessage(message: detectorMessage, isError: false)
        }

        VStack(alignment: .leading, spacing: 8) {
            Text("Country")
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(SeasonlyColors.ink)

            Picker("Country", selection: Binding(
                get: { selectedCountryCode ?? "" },
                set: { selectedCountryCode = $0.isEmpty ? nil : $0 }
            )) {
                Text("Select country").tag("")
                ForEach(countries) { country in
                    Text(country.displayName)
                        .foregroundStyle(country.seasonalDataAvailable ? .primary : .secondary)
                        .tag(country.code)
                        .disabled(!country.seasonalDataAvailable)
                }
            }
            .pickerStyle(.menu)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 14)
            .frame(height: 54)
            .background(Color.white.opacity(0.78), in: RoundedRectangle(cornerRadius: 12))
            .overlay {
                RoundedRectangle(cornerRadius: 12)
                    .stroke(Color.black.opacity(0.08), lineWidth: 1)
            }
        }

        if locationMethod == .device {
            Text("You can correct the detected country before continuing.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }
}

private struct AllergyQuestionPage: View {
    @Binding var selection: AllergyAnswer?

    var body: some View {
        PageIntro(
            title: "Do you have any food allergies?",
            subtitle: "The question is required, but you can choose not to disclose details."
        )

        VStack(spacing: 12) {
            ForEach([AllergyAnswer.none, .provided, .preferNotToSay]) { answer in
                Button {
                    selection = answer
                } label: {
                    MethodRow(
                        icon: selection == answer ? "checkmark.circle.fill" : "circle",
                        title: answer.title,
                        detail: answer == .preferNotToSay ? "Recipes cannot be filtered for allergies." : nil,
                        isSelected: selection == answer
                    )
                }
                .buttonStyle(.plain)
            }
        }
    }
}

private struct AllergensPage: View {
    let options: [EnumReference]
    @Binding var selection: Set<String>
    @Binding var consent: Bool

    var body: some View {
        PageIntro(
            title: "Select allergens",
            subtitle: "Choose one or more. These are safety exclusions, not diet preferences."
        )

        ChipGrid(options: options.map { ChoiceOption(value: $0.value, label: $0.label, detail: nil) }, selection: $selection)

        Toggle(isOn: $consent) {
            Text("I consent to Seasonly storing and using this allergy information to filter recipes.")
                .font(.subheadline)
                .foregroundStyle(SeasonlyColors.ink)
        }
        .toggleStyle(.switch)
        .padding(14)
        .background(Color.white.opacity(0.74), in: RoundedRectangle(cornerRadius: 12))
    }
}

private struct DietaryRulesPage: View {
    @Binding var selection: Set<String>
    @State private var noneSelected = false

    var body: some View {
        PageIntro(
            title: "Foods avoided",
            subtitle: "Are there foods you avoid for personal, cultural or religious reasons?"
        )

        Button {
            noneSelected.toggle()
            if noneSelected { selection.removeAll() }
        } label: {
            MethodRow(icon: noneSelected ? "checkmark.circle.fill" : "circle", title: "None of these", detail: nil, isSelected: noneSelected)
        }
        .buttonStyle(.plain)

        ChipGrid(options: DietaryRuleOption.all, selection: Binding(
            get: { selection },
            set: { newValue in
                selection = newValue
                noneSelected = false
            }
        ))
    }
}

private struct CuisinesPage: View {
    let cuisines: [CuisineReference]
    @Binding var selectedCuisines: [String]
    @Binding var noPreference: Bool

    var body: some View {
        PageIntro(
            title: "Favourite cuisines",
            subtitle: "Choose up to five cuisines supported by the recipe data, or choose no preference."
        )

        Button {
            noPreference.toggle()
            if noPreference { selectedCuisines.removeAll() }
        } label: {
            MethodRow(icon: noPreference ? "checkmark.circle.fill" : "circle", title: "No preference", detail: nil, isSelected: noPreference)
        }
        .buttonStyle(.plain)

        LazyVGrid(columns: [GridItem(.adaptive(minimum: 130), spacing: 10)], spacing: 10) {
            ForEach(cuisines) { cuisine in
                ChipButton(
                    title: cuisine.area,
                    isSelected: selectedCuisines.contains(cuisine.area),
                    isDisabled: !selectedCuisines.contains(cuisine.area) && selectedCuisines.count >= 5
                ) {
                    if selectedCuisines.contains(cuisine.area) {
                        selectedCuisines.removeAll { $0 == cuisine.area }
                    } else if selectedCuisines.count < 5 {
                        selectedCuisines.append(cuisine.area)
                        noPreference = false
                    }
                }
            }
        }
    }
}

private struct ProteinsPage: View {
    let options: [EnumReference]
    @Binding var selectedProteins: [String]

    var body: some View {
        PageIntro(
            title: "Favourite proteins",
            subtitle: "Choose up to five compatible proteins. Allergy and avoided-food conflicts are hidden."
        )

        LazyVGrid(columns: [GridItem(.adaptive(minimum: 130), spacing: 10)], spacing: 10) {
            ForEach(options) { option in
                ChipButton(
                    title: option.label,
                    isSelected: selectedProteins.contains(option.value),
                    isDisabled: !selectedProteins.contains(option.value) && selectedProteins.count >= 5
                ) {
                    if selectedProteins.contains(option.value) {
                        selectedProteins.removeAll { $0 == option.value }
                    } else if selectedProteins.count < 5 {
                        selectedProteins.append(option.value)
                    }
                }
            }
        }
    }
}

private struct ReviewPage: View {
    let countryName: String
    let regionCode: String?
    let diet: String
    let allergyAnswer: String?
    let allergens: [String]
    let dietaryRules: [String]
    let cuisines: [String]
    let proteins: [String]
    let edit: (OnboardingPage) -> Void

    var body: some View {
        PageIntro(
            title: "Review your setup",
            subtitle: "Check everything before finishing onboarding."
        )

        VStack(spacing: 10) {
            ReviewRow(title: "Location", value: [countryName, regionCode].compactMap { $0 }.joined(separator: ", "), page: .confirmLocation, edit: edit)
            ReviewRow(title: "Diet", value: diet, page: .diet, edit: edit)
            ReviewRow(title: "Allergies", value: allergySummary, page: .allergyQuestion, edit: edit)
            ReviewRow(title: "Foods avoided", value: dietaryRules.joined(separator: ", "), page: .dietaryRules, edit: edit)
            ReviewRow(title: "Cuisines", value: cuisines.joined(separator: ", "), page: .cuisines, edit: edit)
            if !proteins.isEmpty {
                ReviewRow(title: "Proteins", value: proteins.joined(separator: ", "), page: .proteins, edit: edit)
            }
        }
    }

    private var allergySummary: String {
        if !allergens.isEmpty { return allergens.joined(separator: ", ") }
        return allergyAnswer ?? "Not selected"
    }
}

private struct SingleChoicePage: View {
    let title: String
    let subtitle: String
    let options: [ChoiceOption]
    @Binding var selection: String?

    var body: some View {
        PageIntro(title: title, subtitle: subtitle)
        VStack(spacing: 12) {
            ForEach(options) { option in
                Button {
                    selection = option.value
                } label: {
                    MethodRow(
                        icon: selection == option.value ? "checkmark.circle.fill" : "circle",
                        title: option.label,
                        detail: option.detail,
                        isSelected: selection == option.value
                    )
                }
                .buttonStyle(.plain)
            }
        }
    }
}

private struct PageIntro: View {
    let title: String
    let subtitle: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.title2.weight(.bold))
                .foregroundStyle(SeasonlyColors.ink)
            Text(subtitle)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }
}

private struct InfoRow: View {
    let icon: String
    let text: String

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: icon)
                .foregroundStyle(SeasonlyColors.brown)
                .frame(width: 24)
            Text(text)
                .font(.subheadline)
                .foregroundStyle(SeasonlyColors.ink)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(14)
        .background(Color.white.opacity(0.72), in: RoundedRectangle(cornerRadius: 12))
    }
}

private struct MethodRow: View {
    let icon: String
    let title: String
    let detail: String?
    let isSelected: Bool

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 18, weight: .semibold))
                .foregroundStyle(isSelected ? SeasonlyColors.brown : .secondary)
                .frame(width: 28)

            VStack(alignment: .leading, spacing: 3) {
                Text(title)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(SeasonlyColors.ink)
                if let detail {
                    Text(detail)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(14)
        .background(Color.white.opacity(isSelected ? 0.88 : 0.68), in: RoundedRectangle(cornerRadius: 12))
        .overlay {
            RoundedRectangle(cornerRadius: 12)
                .stroke(isSelected ? SeasonlyColors.brown.opacity(0.55) : Color.black.opacity(0.08), lineWidth: 1)
        }
    }
}

private struct ChipGrid: View {
    let options: [ChoiceOption]
    @Binding var selection: Set<String>

    var body: some View {
        LazyVGrid(columns: [GridItem(.adaptive(minimum: 130), spacing: 10)], spacing: 10) {
            ForEach(options) { option in
                ChipButton(title: option.label, isSelected: selection.contains(option.value), isDisabled: false) {
                    if selection.contains(option.value) {
                        selection.remove(option.value)
                    } else {
                        selection.insert(option.value)
                    }
                }
            }
        }
    }
}

private struct ChipButton: View {
    let title: String
    let isSelected: Bool
    let isDisabled: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.subheadline.weight(.semibold))
                .lineLimit(2)
                .minimumScaleFactor(0.8)
                .multilineTextAlignment(.center)
                .foregroundStyle(isSelected ? Color.white : SeasonlyColors.ink)
                .frame(maxWidth: .infinity)
                .frame(height: 44)
                .padding(.horizontal, 8)
                .background(isSelected ? SeasonlyColors.brown : Color.white.opacity(0.72), in: RoundedRectangle(cornerRadius: 10))
                .overlay {
                    RoundedRectangle(cornerRadius: 10)
                        .stroke(Color.black.opacity(isSelected ? 0 : 0.08), lineWidth: 1)
                }
        }
        .buttonStyle(.plain)
        .disabled(isDisabled)
        .opacity(isDisabled ? 0.45 : 1)
    }
}

private struct ReviewRow: View {
    let title: String
    let value: String
    let page: OnboardingPage
    let edit: (OnboardingPage) -> Void

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
                Text(value.isEmpty ? "None" : value)
                    .font(.subheadline)
                    .foregroundStyle(SeasonlyColors.ink)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            Button("Edit") { edit(page) }
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(SeasonlyColors.brown)
        }
        .padding(14)
        .background(Color.white.opacity(0.72), in: RoundedRectangle(cornerRadius: 12))
    }
}

@MainActor
@Observable
final class LocationDetector: NSObject, CLLocationManagerDelegate {
    private let manager = CLLocationManager()
    private var onDetected: ((String, String?) -> Void)?
    private var onFallback: (() -> Void)?
    private var timeoutWorkItem: DispatchWorkItem?

    var isDetecting = false
    var message: String?

    func detect(onDetected: @escaping (String, String?) -> Void, onFallback: @escaping () -> Void) {
        self.onDetected = onDetected
        self.onFallback = onFallback
        manager.delegate = self
        isDetecting = true
        message = nil
        timeoutWorkItem?.cancel()
        let timeoutWorkItem = DispatchWorkItem { [weak self] in
            guard let self, self.isDetecting else { return }
            self.failToManual("Location detection took too long, so manual selection is shown.")
        }
        self.timeoutWorkItem = timeoutWorkItem
        DispatchQueue.main.asyncAfter(deadline: .now() + 8, execute: timeoutWorkItem)

        switch manager.authorizationStatus {
        case .notDetermined:
            manager.requestWhenInUseAuthorization()
        case .authorizedAlways, .authorizedWhenInUse:
            manager.requestLocation()
        case .denied, .restricted:
            failToManual("Location permission was unavailable, so manual selection is shown.")
        @unknown default:
            failToManual("Location could not be detected, so manual selection is shown.")
        }
    }

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        switch manager.authorizationStatus {
        case .authorizedAlways, .authorizedWhenInUse:
            manager.requestLocation()
        case .denied, .restricted:
            failToManual("Location permission was unavailable, so manual selection is shown.")
        case .notDetermined:
            break
        @unknown default:
            failToManual("Location could not be detected, so manual selection is shown.")
        }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else {
            failToManual("Location could not be detected, so manual selection is shown.")
            return
        }

        Task {
            do {
                guard let request = MKReverseGeocodingRequest(location: location) else {
                    failToManual("Location lookup failed, so manual selection is shown.")
                    return
                }
                let mapItems = try await request.mapItems
                guard let countryCode = mapItems.compactMap({ $0.placemark.countryCode }).first else {
                    failToManual("Country could not be detected, so manual selection is shown.")
                    return
                }
                finishDetection("Detected location. Please confirm before continuing.")
                onDetected?(countryCode, nil)
            } catch {
                failToManual("Location lookup failed, so manual selection is shown.")
            }
        }
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        failToManual("Location could not be detected, so manual selection is shown.")
    }

    func stopDetecting(message: String? = nil) {
        timeoutWorkItem?.cancel()
        manager.stopUpdatingLocation()
        isDetecting = false
        if let message {
            self.message = message
        }
    }

    private func failToManual(_ message: String) {
        timeoutWorkItem?.cancel()
        manager.stopUpdatingLocation()
        isDetecting = false
        self.message = message
        onFallback?()
    }

    private func finishDetection(_ message: String) {
        timeoutWorkItem?.cancel()
        isDetecting = false
        self.message = message
    }
}

#Preview {
    OnboardingView(session: AuthenticationSession())
}
