# TODO: Review functions and variables names and ensure that they
#   ..  have meaningful names that represent what they do.


import calendar
import datetime

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models.functions import Lower
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, UpdateView
from river.models.fields.state import State

from .forms import AbsenceForm, CreateTeamForm, DeleteUserForm
from .models import Absence, Relationship, Role, Team

User = get_user_model()


# TODO: Move these global variables to be local variables. They must be local variables as this data is not a constant. It changes every day ^_^.
#       ... and by defining these variables as global variables they will stay the same until the app is restarted and the module is reloaded


def index(request) -> render:
    """returns the home page"""
    return render(request, "ap_app/index.html")


def privacy_page(request) -> render:
    return render(request, "ap_app/privacy.html")


class SignUpView(CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy("login")
    template_name = "registration/signup.html"


@login_required
def teams_dashboard(request) -> render:
    rels = Relationship.objects.order_by(Lower("team__name")).filter(
        user=request.user, status=State.objects.get(slug="active")
    )
    invite_rel_count = Relationship.objects.filter(
        user=request.user, status=State.objects.get(slug="invited")
    ).count()
    return render(
        request,
        "teams/dashboard.html",
        {"rels": rels, "invite_count": invite_rel_count},
    )


@login_required
def create_team(request) -> render:
    if request.method == "POST":
        form = CreateTeamForm(request.POST)
        if form.is_valid():
            form.save()
            # Gets the created team and "Owner" Role and creates a Link between the user and their team
            created_team = Team.objects.get(name=form.cleaned_data["name"])
            assign_role = Role.objects.get(role="Owner")
            Relationship.objects.create(
                user=request.user,
                team=created_team,
                role=assign_role,
                status=State.objects.get(slug="active"),
            )
            return redirect("/teams/")
    else:
        form = CreateTeamForm()
    return render(request, "teams/create_team.html", {"form": form})


@login_required
def join_team(request) -> render:
    """Renders page with all teams the user is not currently in"""
    user_teams = []
    all_user_teams = Relationship.objects.all().filter(user=request.user)
    for teams in all_user_teams:
        user_teams.append(teams.team.name)
    all_teams = Team.objects.all().exclude(name__in=user_teams)
    return render(request, "teams/join_team.html", {"all_teams": all_teams})


@login_required
def joining_team_process(request, id, role):
    find_team = Team.objects.get(id=id)
    find_role = Role.objects.get(role=role)
    new_rel = Relationship.objects.create(
        user=request.user,
        team=find_team,
        role=find_role,
        status=State.objects.get(slug="pending"),
    )
    if not find_team.private:
        Relationship.objects.filter(id=new_rel.id).update(
            status=State.objects.get(slug="active")
        )

    return redirect("dashboard")


def team_invite(request, team_id, user_id, role):
    find_team = Team.objects.get(id=team_id)
    find_user = User.objects.get(id=user_id)
    find_role = Role.objects.get(role=role)
    Relationship.objects.create(
        user=find_user,
        team=find_team,
        role=find_role,
        status=State.objects.get(slug="invited"),
    )
    return redirect("dashboard")


@login_required
def view_invites(request):
    all_invites = Relationship.objects.filter(
        user=request.user, status=State.objects.get(slug="invited")
    )
    return render(request, "teams/invites.html", {"invites": all_invites})


@login_required
def leave_team(request, id):
    find_relationship = Relationship.objects.get(id=id)
    find_relationship.custom_delete()
    team_cleaner(find_relationship)
    return redirect("dashboard")


def team_cleaner(rel):
    team = Team.objects.get(id=rel.team.id)
    all_team_relationships = Relationship.objects.filter(team=team)
    if all_team_relationships.count() == 0:
        team.delete()
    return


@login_required
def team_settings(request, id):
    """Checks to see if user is the owner and renders the Setting page"""
    team = Team.objects.get(id=id)
    user_relation = Relationship.objects.get(team=id, user=request.user)
    if user_relation.role.role == "Owner":
        all_pending_relations = Relationship.objects.filter(
            team=id, status=State.objects.get(slug="pending")
        )
        return render(
            request,
            "teams/settings.html",
            {"team": team, "pending_rels": all_pending_relations},
        )

    return redirect("dashboard")


def joining_team_request(request, id, response):
    find_rel = Relationship.objects.get(id=id)
    if response == "accepted":
        state_response = State.objects.get(slug="active")
    elif response == "nonactive":
        state_response = State.objects.get(slug="nonactive")
    Relationship.objects.filter(id=find_rel.id).update(status=state_response)

    return redirect("dashboard")


@login_required
def add(request) -> render:
    """create new absence record"""
    if request.method == "POST":
        form = AbsenceForm(request.POST)
        if form.is_valid():
            obj = Absence()
            obj.absence_date_start = form.cleaned_data["start_date"]
            obj.absence_date_end = form.cleaned_data["end_date"]
            obj.request_accepted = False
            obj.User_ID = request.user
            obj.save()

            # redirect to success page
    else:
        form = AbsenceForm()
    content = {"form": form}
    return render(request, "ap_app/add_absence.html", content)


@login_required
def details_page(request) -> render:
    """returns details web page"""
    # TODO: get employee details and add them to context
    context = {"employee_dicts": ""}
    return render(request, "ap_app/Details.html", context)


def get_date_data(month, year):
    data = {}
    data["current_year"] = year
    data["current_month"] = month
    data["year"] = data["current_year"]
    data["month"] = data["current_month"]
    data["day_range"] = range(
        1,
        calendar.monthrange(
            data["year"], datetime.datetime.strptime(data["month"], "%B").month
        )[1]
        + 1,
    )
    data["month_num"] = datetime.datetime.strptime(data["month"], "%B").month

    data["previous_month"] = 12
    data["next_month"] = 1
    data["previous_year"] = data["year"] - 1
    data["next_year"] = data["year"] + 1

    try:

        data["next_month"] = datetime.datetime.strptime(
            str((datetime.datetime.strptime(data["month"], "%B")).month + 1), "%m"
        ).strftime("%B")
    except ValueError:
        pass
    try:
        data["previous_month"] = datetime.datetime.strptime(
            str((datetime.datetime.strptime(data["month"], "%B")).month - 1), "%m"
        ).strftime("%B")
    except ValueError:
        pass
    data["day_names"] = []
    month = data["month"]
    year = data["year"]
    for day in data["day_range"]:
        date = f"{day} {month} {year}"
        date = datetime.datetime.strptime(date, "%d %B %Y")
        date = date.strftime("%A")[0:2]
        data["day_names"].append(date)

    return data


def get_user_data(users):
    data = {}
    absence_content = []
    total_absence_dates = {}
    all_absences = {}
    delta = datetime.timedelta(days=1)

    for user in users:
        # all the absences for the user
        absence_info = Absence.objects.filter(User_ID=user.user.id)
        total_absence_dates[user] = []
        all_absences[user] = []

        # if they have any absences
        if absence_info:
            # mapping the absence content to keys in dictionary
            for i, x in enumerate(absence_info):
                absence_id = x.ID
                absence_date_start = x.absence_date_start
                absence_date_end = x.absence_date_end
                dates = absence_date_start
                while dates <= absence_date_end:
                    total_absence_dates[user].append(dates)
                    dates += delta

                absence_content.append(
                    {
                        "ID": absence_id,
                        "absence_date_start": absence_date_start,
                        "absence_date_end": absence_date_end,
                        "dates": total_absence_dates[user],
                    }
                )

            # for each user it maps the set of dates to a dictionary key labelled as the users name
            total_absence_dates[user] = total_absence_dates[user]
            all_absences[user] = absence_content
        else:
            total_absence_dates[user] = []
            all_absences[user] = []

    data["absence_dates"] = total_absence_dates

    return data


# TODO: team_calender and all_calender seem to have duplicate code. DRY (Don't repeat yourself) principle
@login_required
def team_calendar(
    request,
    id,
    month=datetime.datetime.now().strftime("%B"),
    year=datetime.datetime.now().year,
):
    data_1 = get_date_data(month, year)

    users = Relationship.objects.all().filter(
        team=id, status=State.objects.get(slug="active")
    )
    print(users)
    data_2 = get_user_data(users)

    team = Team.objects.get(id=id)

    user_in_teams = []
    for rel in Relationship.objects.filter(team=team):
        user_in_teams.append(rel.user.id)

    data_3 = {
        "current_user": Relationship.objects.get(user=request.user, team=team),
        "team": team,
        "all_users": User.objects.all().exclude(id__in=user_in_teams),
        "team_count": Relationship.objects.filter(
            team=team.id, status=State.objects.get(slug="active")
        ).count(),
    }

    context = {**data_1, **data_2, **data_3}
    return render(request, "teams/calendar.html", context)


@login_required
def all_calendar(
    request,
    month=datetime.datetime.now().strftime("%B"),
    year=datetime.datetime.now().year,
):
    data_1 = get_date_data(month, year)

    all_users = []
    all_users.append(request.user)
    user_relations = Relationship.objects.filter(user=request.user)
    for relation in user_relations:
        rels = Relationship.objects.filter(
            team=relation.team, status=State.objects.get(slug="active")
        )
        for rel in rels:
            if rel.user in all_users:
                pass
            else:
                all_users.append(rel.user)
    print(all_users)
    data_2 = get_user_data(all_users)

    data_3 = {"Sa": "Sa", "Su": "Su"}

    context = {**data_1, **data_2, **data_3}

    return render(request, "ap_app/calendar.html", context)


# Profile page
@login_required
def profile_page(request):
    absences = Absence.objects.filter(User_ID=request.user.id)
    return render(request, "ap_app/profile.html", {"absences": absences})


@login_required
def deleteuser(request):
    """delete a user account"""
    if request.method == "POST":
        delete_form = DeleteUserForm(request.POST, instance=request.user)
        user = request.user
        user.delete()
        messages.info(request, "Your account has been deleted.")
        return redirect("index")
    else:
        delete_form = DeleteUserForm(instance=request.user)

    context = {"delete_form": delete_form}

    return render(request, "registration/delete_account.html", context)


@login_required
def absence_delete(request, absence_id: int):
    absence = Absence.objects.get(pk=absence_id)
    user = request.user
    if user == absence.User_ID:
        absence.delete()
        return redirect("profile")
    else:
        raise Exception()


class EditAbsence(UpdateView):
    template_name = "ap_app/edit_absence.html"
    model = Absence

    # specify the fields
    fields = ["absence_date_start", "absence_date_end"]

    def get_success_url(self) -> str:
        return reverse("profile")


@login_required
def profile_settings(request) -> render:
    """returns the settings page"""
    absences = Absence.objects.filter(User_ID=request.user.id)
    context = {"absences": absences}
    return render(request, "ap_app/settings.html", context)


@login_required
def add_user(request) -> render:
    if request.method == "POST":
        username = request.POST.get("username")
        try:
            absence: Absence = Absence.objects.filter(User_ID=request.user.id)[0]
        except IndexError:
            # TODO Create error page
            return redirect("/")

        try:
            user = User.objects.filter(username=username)[0]
        except IndexError:
            # TODO Create error page
            return redirect("/")

        absence.edit_whitelist.add(user)
        absence.save()
    return redirect("/profile/settings")
